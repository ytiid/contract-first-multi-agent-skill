#!/usr/bin/env python3
"""Audit changed paths against work-item and integration ownership."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path


def git(args: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode, (proc.stdout if proc.returncode == 0 else proc.stderr).strip()


def match_path(path: str, pattern: str) -> bool:
    path = path.strip("/")
    pattern = pattern.strip("/")
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory")
    parser.add_argument("--base", help="Override manifest base SHA/ref")
    parser.add_argument("--include-untracked", action="store_true")
    parser.add_argument(
        "--strict-preexisting",
        action="store_true",
        help="Treat changed paths that already differed from base at run start as audit errors",
    )
    args = parser.parse_args()

    run_dir = Path(args.run_directory).expanduser().resolve()
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8-sig"))
    work_data = json.loads((run_dir / "40-work-items.json").read_text(encoding="utf-8-sig"))
    repo_root = Path(manifest["repo_root"])
    base = args.base or manifest.get("base_sha") or manifest.get("base_ref") or "HEAD"

    if not manifest.get("is_git", True) or base == "NON_GIT":
        parser.error("diff-scope audit requires a Git repository")

    rc, output = git(["diff", "--name-only", base, "--"], repo_root)
    if rc != 0:
        parser.error(output)
    changed = {line.strip() for line in output.splitlines() if line.strip()}

    if args.include_untracked:
        rc, untracked = git(["ls-files", "--others", "--exclude-standard"], repo_root)
        if rc != 0:
            parser.error(untracked)
        changed.update(line.strip() for line in untracked.splitlines() if line.strip())

    integration_owned = work_data.get("integration_owned", [])
    items = work_data.get("items", [])
    preexisting = set(manifest.get("preexisting_paths", []))
    errors: list[str] = []
    warnings: list[str] = []

    print(f"Base: {base}")
    print(f"Changed paths: {len(changed)}")
    for path in sorted(changed):
        item_owners = [
            item.get("id", "<unknown>")
            for item in items
            if any(match_path(path, pattern) for pattern in item.get("write_set", []))
        ]
        integration_match = any(match_path(path, pattern) for pattern in integration_owned)
        labels = item_owners + (["MAIN/INTEGRATION"] if integration_match else [])
        existed = path in preexisting
        if not labels:
            if existed and not args.strict_preexisting:
                label = "PREEXISTING"
                warnings.append(f"pre-existing path remains different from base: {path}")
            else:
                errors.append(f"unowned changed path: {path}")
                label = "UNOWNED"
        elif len(labels) > 1:
            errors.append(f"multiply owned changed path: {path} -> {', '.join(labels)}")
            label = "MULTIPLE: " + ", ".join(labels)
        else:
            label = labels[0]
            if existed:
                label = "PREEXISTING+" + label
                warnings.append(f"owned path overlapped the pre-existing diff and needs hunk-level review: {path}")
        print(f"{label:24} {path}")

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
