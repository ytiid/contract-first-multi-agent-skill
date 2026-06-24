# Contract and work-item specification

## Contents

- Task envelope
- Implementation contract
- Acceptance criteria
- Work-item schema
- Worker contract header
- Contract change discipline

## Task envelope

Keep the task envelope compact and stable:

```text
TASK_ID:
OBJECTIVE:
USER-VISIBLE OUTCOME:
BASE_REF / BASE_SHA:
IN-SCOPE:
OUT-OF-SCOPE:
CONSTRAINTS:
KNOWN ASSUMPTIONS:
REQUIRED CHECKS:
MODE:
WRITE STRATEGY:
```

The main agent owns this envelope. Subagents may identify ambiguity but may not rewrite user intent.

## Implementation contract

`30-contract.md` must contain these headings:

1. `Objective`
2. `Current behavior`
3. `Target behavior`
4. `Scope`
5. `Non-goals`
6. `Interfaces and data contracts`
7. `Invariants`
8. `Compatibility and migration`
9. `Error, logging, and observability semantics`
10. `Security, concurrency, and performance constraints`
11. `Acceptance criteria`
12. `Validation plan`
13. `Ownership and integration boundaries`
14. `Rollback or recovery`
15. `Assumptions and open decisions`
16. `Decision log`

At the top include:

```text
Status: DRAFT | FROZEN
Version: <integer>
Hash: <pending or sha256>
Base SHA: <sha>
```

### Contract quality tests

A contract is ready to freeze only when:

- every target behavior is externally observable or testable;
- public API/type/schema changes are explicit;
- error cases and backward compatibility are explicit;
- invariants are stated independently of implementation details;
- every acceptance criterion maps to a validation method;
- ownership boundaries can be derived without overlapping writers;
- no blocking assumption remains hidden;
- non-goals prevent plausible scope creep.

Avoid prescribing incidental implementation details unless they are required for compatibility, safety, or architecture consistency.

## Acceptance criteria style

Use stable identifiers:

```text
AC-01: Given <precondition>, when <action>, then <observable result>.
Evidence: <test/command/inspection planned>
```

Include negative and edge behavior where material. For migrations, include forward compatibility, rollback/retry behavior, and partial-failure semantics.

## Work-item schema

`40-work-items.json` has this shape:

```json
{
  "contract_version": 1,
  "contract_hash": "sha256",
  "integration_owned": ["path/or/glob"],
  "items": [
    {
      "id": "WI-01",
      "goal": "One bounded outcome",
      "owner_role": "implementation_worker",
      "delegation_agent_type": "worker",
      "depends_on": [],
      "contract_clauses": ["AC-01"],
      "read_set": ["src/**"],
      "write_set": ["src/module.py", "tests/test_module.py"],
      "no_touch": ["package-lock.json"],
      "acceptance_commands": ["pytest tests/test_module.py -q"],
      "parallel_group": "wave-1",
      "integration_order": 10
    }
  ]
}
```

Prefer exact paths. Use globs only for genuinely cohesive ownership. Treat lockfiles, generated code, migrations, central indexes, global schemas, and shared configuration as integration-owned unless one item exclusively owns them.

`delegation_agent_type` is required. Use `worker` by default because it is the stable built-in implementation agent type. Use `implementation_worker` only when that installed custom role is visible in the current tool surface. Do not leave implementation items as main-agent tasks in Plan-mode output.

## Worker contract header

Every worker receives and echoes:

```text
CONTRACT_VERSION:
CONTRACT_HASH:
WORK_ITEM_ID:
BASE_SHA:
ALLOWED_WRITE_SET:
NO_TOUCH:
DEPENDENCIES_ACCEPTED:
```

A mismatched version/hash invalidates the report.

## Contract change discipline

After freeze, only the main agent can edit the contract. Any semantic change requires:

1. status back to `DRAFT`;
2. decision-log entry explaining why;
3. new critique of changed clauses;
4. version increment;
5. new hash;
6. update of affected work items;
7. explicit invalidation or revalidation of worker reports tied to the old hash.
