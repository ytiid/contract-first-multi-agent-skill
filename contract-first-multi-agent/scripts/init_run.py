#!/usr/bin/env python3
"""Initialize a local run workspace for the contract-first multi-agent skill."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


def run_git(args: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    output = proc.stdout.strip() if proc.returncode == 0 else proc.stderr.strip()
    return proc.returncode, output


def slugify(value: str, max_len: int = 48) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return (value or "task")[:max_len].rstrip("-")


def replace_placeholders(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="Compact task objective")
    parser.add_argument("--mode", choices=["quick", "lite", "standard", "deep", "strict"], default="standard")
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument("--repo", default=".", help="Repository or project path")
    parser.add_argument("--run-root", help="Override run root; default is <repo>/.codex/workflows")
    parser.add_argument("--run-id", help="Override generated run id")
    parser.add_argument(
        "--add-info-exclude",
        action="store_true",
        help="Add /.codex/workflows/ to .git/info/exclude for this repository",
    )
    args = parser.parse_args()

    start = Path(args.repo).expanduser().resolve()
    if not start.exists():
        parser.error(f"repository path does not exist: {start}")

    git_ok, repo_text = run_git(["rev-parse", "--show-toplevel"], start)
    is_git = git_ok == 0
    repo_root = Path(repo_text).resolve() if is_git else start

    if is_git:
        rc, base_sha = run_git(["rev-parse", args.base_ref], repo_root)
        if rc != 0:
            parser.error(f"cannot resolve base ref {args.base_ref!r}: {base_sha}")
        _, head_sha = run_git(["rev-parse", "HEAD"], repo_root)
        _, branch = run_git(["branch", "--show-current"], repo_root)
        _, git_status = run_git(["status", "--short"], repo_root)
        _, diff_paths_text = run_git(["diff", "--name-only", base_sha, "--"], repo_root)
        _, untracked_text = run_git(["ls-files", "--others", "--exclude-standard"], repo_root)
        _, git_diff_stat = run_git(["diff", "--stat", base_sha, "--"], repo_root)
        preexisting_paths = sorted(
            {line.strip() for line in (diff_paths_text + "\n" + untracked_text).splitlines() if line.strip()}
        )
        branch = branch or "DETACHED"
        git_diff_stat = git_diff_stat or "No tracked difference from base."
    else:
        base_sha = "NON_GIT"
        head_sha = "NON_GIT"
        branch = "NON_GIT"
        git_status = "Non-Git project; capture a filesystem baseline manually."
        git_diff_stat = "Non-Git project; capture a filesystem baseline manually."
        preexisting_paths = []

    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = args.run_id or f"{timestamp}-{slugify(args.task)}"
    run_root = Path(args.run_root).expanduser().resolve() if args.run_root else repo_root / ".codex" / "workflows"
    run_dir = run_root / run_id
    if run_dir.exists():
        parser.error(f"run directory already exists: {run_dir}")

    run_dir.mkdir(parents=True)
    (run_dir / "10-recon").mkdir()
    (run_dir / "50-worker-reports").mkdir()

    skill_root = Path(__file__).resolve().parent.parent
    template_root = skill_root / "assets" / "run"
    values = {
        "RUN_ID": run_id,
        "CREATED_AT": dt.datetime.now(dt.timezone.utc).isoformat(),
        "MODE": args.mode,
        "REPO_ROOT": str(repo_root),
        "BRANCH": branch,
        "BASE_REF": args.base_ref,
        "BASE_SHA": base_sha,
        "TASK": args.task,
        "GIT_STATUS": git_status or "Clean",
        "GIT_DIFF_STAT": git_diff_stat,
    }

    copies = {
        "00-request.md": run_dir / "00-request.md",
        "20-synthesis.md": run_dir / "20-synthesis.md",
        "30-contract.md": run_dir / "30-contract.md",
        "40-work-items.json": run_dir / "40-work-items.json",
        "60-integration-review.md": run_dir / "60-integration-review.md",
        "70-validation.md": run_dir / "70-validation.md",
        "80-final.md": run_dir / "80-final.md",
        "recon-report.md": run_dir / "10-recon" / "REPORT_TEMPLATE.md",
        "worker-report.md": run_dir / "50-worker-reports" / "REPORT_TEMPLATE.md",
    }

    for source_name, destination in copies.items():
        source = template_root / source_name
        text = replace_placeholders(source.read_text(encoding="utf-8"), values)
        destination.write_text(text, encoding="utf-8")

    manifest = {
        "run_id": run_id,
        "created_at": values["CREATED_AT"],
        "mode": args.mode,
        "task": args.task,
        "repo_root": str(repo_root),
        "is_git": is_git,
        "branch": branch,
        "head_sha": head_sha,
        "base_ref": args.base_ref,
        "base_sha": base_sha,
        "preexisting_status": git_status,
        "preexisting_diff_stat": git_diff_stat,
        "preexisting_paths": preexisting_paths,
        "contract_version": 1,
        "contract_hash": "<pending>",
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if args.add_info_exclude and is_git:
        rc, git_dir_text = run_git(["rev-parse", "--git-dir"], repo_root)
        if rc == 0:
            git_dir = Path(git_dir_text)
            if not git_dir.is_absolute():
                git_dir = (repo_root / git_dir).resolve()
            exclude = git_dir / "info" / "exclude"
            exclude.parent.mkdir(parents=True, exist_ok=True)
            existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
            entry = "/.codex/workflows/"
            if entry not in existing.splitlines():
                with exclude.open("a", encoding="utf-8") as handle:
                    if existing and not existing.endswith("\n"):
                        handle.write("\n")
                    handle.write(entry + "\n")

    print(run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
