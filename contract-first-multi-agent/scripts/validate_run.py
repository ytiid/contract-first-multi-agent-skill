#!/usr/bin/env python3
"""Validate workflow artifacts, contract integrity, dependencies, and parallel write ownership."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REQUIRED_FILES = [
    "manifest.json",
    "00-request.md",
    "20-synthesis.md",
    "30-contract.md",
    "40-work-items.json",
    "60-integration-review.md",
    "70-validation.md",
]

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

REQUIRED_ITEM_FIELDS = {
    "id",
    "goal",
    "owner_role",
    "delegation_agent_type",
    "depends_on",
    "contract_clauses",
    "read_set",
    "write_set",
    "no_touch",
    "acceptance_commands",
    "parallel_group",
    "integration_order",
}

ALLOWED_DELEGATION_AGENT_TYPES = {"worker", "implementation_worker"}


def meta(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1) if match else None


def normalize_hash(text: str) -> str:
    replaced, count = re.subn(r"^Hash:\s*.*$", "Hash: <pending>", text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError("missing Hash metadata")
    return replaced.replace("\r\n", "\n").rstrip() + "\n"


def digest(text: str) -> str:
    return hashlib.sha256(normalize_hash(text).encode("utf-8")).hexdigest()


def has_magic(pattern: str) -> bool:
    return any(ch in pattern for ch in "*?[")


def match_path(path: str, pattern: str) -> bool:
    path = path.strip("/")
    pattern = pattern.strip("/")
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def obvious_overlap(a: str, b: str) -> bool:
    a = a.strip("/")
    b = b.strip("/")
    if a == b:
        return True
    if not has_magic(a) and match_path(a, b):
        return True
    if not has_magic(b) and match_path(b, a):
        return True
    if a.endswith("/**") and b.endswith("/**"):
        ap = a[:-3].rstrip("/")
        bp = b[:-3].rstrip("/")
        return ap == bp or ap.startswith(bp + "/") or bp.startswith(ap + "/")
    if a.endswith("/**") and not has_magic(b):
        return match_path(b, a)
    if b.endswith("/**") and not has_magic(a):
        return match_path(a, b)
    return False


def require_list(item: dict[str, Any], field: str, errors: list[str], item_id: str) -> list[Any]:
    value = item.get(field)
    if not isinstance(value, list):
        errors.append(f"{item_id}.{field} must be a list")
        return []
    return value


def check_cycles(items: dict[str, dict[str, Any]], errors: list[str]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle_start = stack.index(node) if node in stack else 0
            errors.append("dependency cycle: " + " -> ".join(stack[cycle_start:] + [node]))
            return
        visiting.add(node)
        stack.append(node)
        for dep in items[node].get("depends_on", []):
            if dep in items:
                visit(dep, stack)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for item_id in items:
        visit(item_id, [])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_directory")
    parser.add_argument("--require-frozen", action="store_true")
    parser.add_argument("--require-validation-pass", action="store_true")
    parser.add_argument("--allow-todo", action="store_true")
    args = parser.parse_args()

    run_dir = Path(args.run_directory).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for name in REQUIRED_FILES:
        if not (run_dir / name).exists():
            errors.append(f"missing required file: {name}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    contract_text = (run_dir / "30-contract.md").read_text(encoding="utf-8-sig")
    status = (meta(contract_text, "Status") or "").upper()
    version_text = meta(contract_text, "Version")
    stored_hash = meta(contract_text, "Hash")

    missing_headings = [h for h in REQUIRED_HEADINGS if f"## {h}" not in contract_text]
    if missing_headings:
        errors.append("contract missing headings: " + ", ".join(missing_headings))
    if args.require_frozen and status != "FROZEN":
        errors.append(f"contract is not FROZEN (status={status or 'missing'})")
    if not args.allow_todo and re.search(r"\bTODO\b", contract_text):
        errors.append("contract contains TODO markers")
    try:
        version = int(version_text or "")
        if version < 1:
            raise ValueError
    except ValueError:
        errors.append(f"invalid contract version: {version_text!r}")
        version = -1
    try:
        computed_hash = digest(contract_text)
        if stored_hash not in {None, "<pending>"} and stored_hash != computed_hash:
            errors.append(f"contract hash mismatch: stored={stored_hash}, computed={computed_hash}")
    except ValueError as exc:
        errors.append(str(exc))
        computed_hash = ""

    try:
        work_data = json.loads((run_dir / "40-work-items.json").read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid 40-work-items.json: {exc}")
        work_data = {}

    if not isinstance(work_data, dict):
        errors.append("40-work-items.json root must be an object")
        work_data = {}

    if work_data.get("contract_version") != version:
        errors.append(
            f"work-items contract_version {work_data.get('contract_version')!r} does not match contract {version!r}"
        )
    if status == "FROZEN" and work_data.get("contract_hash") != stored_hash:
        errors.append("work-items contract_hash does not match frozen contract")

    integration_owned = work_data.get("integration_owned", [])
    if not isinstance(integration_owned, list) or not all(isinstance(p, str) for p in integration_owned):
        errors.append("integration_owned must be a list of strings")
        integration_owned = []

    raw_items = work_data.get("items", [])
    if not isinstance(raw_items, list):
        errors.append("items must be a list")
        raw_items = []
    if args.require_frozen and not raw_items:
        errors.append("frozen workflow has no work items")

    items: dict[str, dict[str, Any]] = {}
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            errors.append(f"items[{index}] must be an object")
            continue
        item_id = raw.get("id")
        if not isinstance(item_id, str) or not item_id:
            errors.append(f"items[{index}].id must be a non-empty string")
            item_id = f"<index-{index}>"
        if item_id in items:
            errors.append(f"duplicate work-item id: {item_id}")
        items[item_id] = raw
        missing_fields = sorted(REQUIRED_ITEM_FIELDS - set(raw))
        if missing_fields:
            errors.append(f"{item_id} missing fields: {', '.join(missing_fields)}")
        for field in ["depends_on", "contract_clauses", "read_set", "write_set", "no_touch", "acceptance_commands"]:
            values = require_list(raw, field, errors, item_id)
            if not all(isinstance(v, str) for v in values):
                errors.append(f"{item_id}.{field} must contain only strings")
        if not isinstance(raw.get("goal"), str) or not raw.get("goal", "").strip():
            errors.append(f"{item_id}.goal must be a non-empty string")
        delegation_agent_type = raw.get("delegation_agent_type")
        if delegation_agent_type not in ALLOWED_DELEGATION_AGENT_TYPES:
            errors.append(
                f"{item_id}.delegation_agent_type must be one of: "
                + ", ".join(sorted(ALLOWED_DELEGATION_AGENT_TYPES))
            )
        if not isinstance(raw.get("parallel_group"), str) or not raw.get("parallel_group", "").strip():
            errors.append(f"{item_id}.parallel_group must be a non-empty string")
        else:
            groups[raw["parallel_group"]].append(raw)
        if not isinstance(raw.get("integration_order"), int):
            errors.append(f"{item_id}.integration_order must be an integer")
        for pattern in raw.get("write_set", []):
            if pattern in {"**", "*", "./**"}:
                warnings.append(f"{item_id} has an excessively broad write pattern: {pattern}")
            for shared in integration_owned:
                if obvious_overlap(pattern, shared):
                    errors.append(f"{item_id} write_set {pattern!r} overlaps integration_owned {shared!r}")

    for item_id, item in items.items():
        for dep in item.get("depends_on", []):
            if dep not in items:
                errors.append(f"{item_id} depends on unknown item {dep}")
            if dep == item_id:
                errors.append(f"{item_id} depends on itself")
    check_cycles(items, errors)

    for group, members in groups.items():
        for i, left in enumerate(members):
            for right in members[i + 1 :]:
                for a in left.get("write_set", []):
                    for b in right.get("write_set", []):
                        if obvious_overlap(a, b):
                            errors.append(
                                f"parallel write overlap in {group}: {left.get('id')}:{a!r} vs {right.get('id')}:{b!r}"
                            )

    if args.require_validation_pass:
        validation_text = (run_dir / "70-validation.md").read_text(encoding="utf-8-sig")
        validation_status = (meta(validation_text, "Status") or "").upper()
        if validation_status != "PASS":
            errors.append(f"validation status is not PASS (status={validation_status or 'missing'})")
        if re.search(r"\bPENDING\b", validation_text):
            errors.append("validation report still contains PENDING markers")

    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")

    if errors:
        return 1
    print(f"OK: workflow artifacts valid; contract v{version} {stored_hash or computed_hash}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
