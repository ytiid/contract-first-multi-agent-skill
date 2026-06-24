#!/usr/bin/env python3
"""Validate, version, hash, and freeze a workflow implementation contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REQUIRED_HEADINGS = [
    "Objective",
    "Current behavior",
    "Target behavior",
    "Scope",
    "Non-goals",
    "Interfaces and data contracts",
    "Invariants",
    "Compatibility and migration",
    "Error, logging, and observability semantics",
    "Security, concurrency, and performance constraints",
    "Acceptance criteria",
    "Validation plan",
    "Ownership and integration boundaries",
    "Rollback or recovery",
    "Assumptions and open decisions",
    "Decision log",
]


def replace_line(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}:\s*.*$", re.MULTILINE)
    replacement = f"{key}: {value}"
    if not pattern.search(text):
        raise ValueError(f"missing metadata line: {key}:")
    return pattern.sub(replacement, text, count=1)


def metadata(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1) if match else None


def normalized_for_hash(text: str) -> str:
    normalized = replace_line(text, "Hash", "<pending>")
    return normalized.replace("\r\n", "\n").rstrip() + "\n"


def contract_hash(text: str) -> str:
    return hashlib.sha256(normalized_for_hash(text).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory")
    parser.add_argument("--version", type=int, help="Explicit positive contract version")
    parser.add_argument("--allow-todo", action="store_true")
    args = parser.parse_args()

    run_dir = Path(args.run_directory).expanduser().resolve()
    contract_path = run_dir / "30-contract.md"
    work_items_path = run_dir / "40-work-items.json"
    manifest_path = run_dir / "manifest.json"

    if not contract_path.exists():
        parser.error(f"missing contract: {contract_path}")

    text = contract_path.read_text(encoding="utf-8-sig")
    missing = [heading for heading in REQUIRED_HEADINGS if f"## {heading}" not in text]
    if missing:
        parser.error("missing required contract headings: " + ", ".join(missing))
    if not args.allow_todo and re.search(r"\bTODO\b", text):
        parser.error("contract still contains TODO markers; replace them or pass --allow-todo deliberately")

    current_version_text = metadata(text, "Version")
    current_status = (metadata(text, "Status") or "DRAFT").upper()
    try:
        current_version = int(current_version_text or "1")
    except ValueError:
        parser.error(f"invalid Version value: {current_version_text!r}")

    if args.version is not None:
        if args.version < 1:
            parser.error("--version must be positive")
        version = args.version
    elif current_status == "FROZEN":
        version = current_version + 1
    else:
        version = current_version

    text = replace_line(text, "Status", "FROZEN")
    text = replace_line(text, "Version", str(version))
    text = replace_line(text, "Hash", "<pending>")
    digest = contract_hash(text)
    text = replace_line(text, "Hash", digest)
    contract_path.write_text(text.rstrip() + "\n", encoding="utf-8")

    if work_items_path.exists():
        try:
            data = json.loads(work_items_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            parser.error(f"invalid work-items JSON: {exc}")
        data["contract_version"] = version
        data["contract_hash"] = digest
        work_items_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            parser.error(f"invalid manifest JSON: {exc}")
        manifest["contract_version"] = version
        manifest["contract_hash"] = digest
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Frozen contract v{version}: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
