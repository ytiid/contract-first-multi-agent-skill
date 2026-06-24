---
name: contract-first-multi-agent
description: Orchestrate medium-to-large repository changes with parallel read-only reconnaissance, a reviewed and frozen implementation contract, bounded subagent implementation, combined-diff review, and main-agent integration. Use for cross-module features, refactors, migrations, risky fixes, or explicit multi-agent coding workflows. Do not use for trivial one-file edits or when the user requests a direct fast patch.
---

# Contract-First Multi-Agent Development

Use this skill to protect the main thread from exploration noise while preserving architectural control and integration ownership.

## Core ownership model

The main agent owns:

- user intent, assumptions, scope, and non-goals;
- the synthesized repository model;
- the implementation contract and every contract revision;
- work-item boundaries and write ownership;
- acceptance of subagent findings;
- the combined diff, integration fixes, and final validation claim.

Subagents own only bounded evidence gathering, critique, implementation, or review assignments. They do not redefine the task or silently change the contract.

## Delegation authorization and Plan mode

Treat explicit invocation of this skill, including `$contract-first-multi-agent`, as an explicit request to use subagents for reconnaissance, contract criticism, implementation workers, and combined-diff review.

If subagent tools are unavailable, do not silently downgrade to main-agent implementation. State that the workflow is blocked or ask the user to approve a direct fallback.

When operating in Plan mode or any plan-first interaction, the plan itself must preserve the worker-execution protocol. The approved plan is not permission for the main agent to directly edit the implementation. It is permission to execute the frozen-contract workflow by spawning worker agents for ready work items, then integrating their results.

A valid Plan-mode implementation plan must include:

- selected mode and write strategy;
- reasoning-effort profile for reconnaissance, worker, critic, reviewer, and test-auditor agents;
- module-map and module-oriented reconnaissance agents when the user asked for module/package/subsystem analysis;
- contract-freeze gate before implementation;
- worker waves with work-item ids, dependencies, write sets, no-touch paths, acceptance commands, and intended `worker` delegation;
- main-agent-owned integration paths and final validation;
- a statement that the main agent will not implement work-item code directly unless subagent delegation is unavailable and the user explicitly approves that fallback.

A plan whose implementation section only lists files/functions for the main agent to modify is invalid for this skill. Rewrite it as worker waves before asking for approval.

## Non-negotiable rules

1. Do not begin implementation before the contract is marked `FROZEN`.
2. Keep reconnaissance, contract review, and combined-diff review read-only.
3. Never allow concurrent writers to share a file or shared generated artifact.
4. Give every subagent a bounded prompt, explicit input, explicit output schema, and stop condition.
5. Require file-and-symbol evidence for material reconnaissance and review claims.
6. Do not paste raw logs or full subagent transcripts into the main thread. Store detailed reports in the run directory and return distilled conclusions.
7. A worker that discovers a contract defect must report `CONTRACT_BREAK`; it must not improvise a new interface.
8. The main agent makes integration fixes only after reviewing the whole diff against the frozen contract.
9. Never reset, clean, stash, discard, or overwrite user changes. Separate pre-existing changes from workflow changes.
10. Close completed subagent threads before starting the next wave. Keep subagent nesting at one level.
11. Treat `Sequential` write strategy as sequential worker delegation, not main-agent implementation, unless the user explicitly approves a direct fallback.

## Start

1. Read all applicable `AGENTS.md` files and repository guidance.
2. Capture the request, constraints, base revision, branch, working-tree state, and available validation commands.
3. Select `quick`/`lite`, `standard`, or `deep`/`strict` mode using `references/orchestration.md`, including the mode-specific reasoning-effort profile.
4. Resolve `SKILL_DIR` to the directory containing this `SKILL.md`. Create a local run directory with an absolute script path:

```bash
python3 "$SKILL_DIR/scripts/init_run.py" --task "<task>" --mode standard --base-ref HEAD
```

If the script cannot run, create equivalent artifacts manually from `assets/run/`.

5. Record the pre-existing diff before changing any file.

## Workflow

Follow this state machine without skipping gates:

`INTAKE -> RECON -> SYNTHESIS -> CONTRACT_REVIEW -> CONTRACT_FROZEN -> IMPLEMENT -> DIFF_REVIEW -> INTEGRATE -> VALIDATE -> DONE`

Read `references/orchestration.md` for exact gates, scaling, write-isolation policy, and recovery transitions.
Read `references/recovery.md` whenever the working tree is dirty, an agent exceeds scope, a contract breaks, or validation fails.

### Phase 1: parallel reconnaissance

Spawn bounded, read-only subagents. Recon agent count is not fixed. The main agent must choose the smallest sufficient reconnaissance set based on task size, risk, and repository topology:

- **quick/lite:** 2-3 recon agents.
- **standard:** 3-6 recon agents.
- **deep/strict:** 6-10 recon agents, launched in waves when useful or when thread budget requires it.

Apply the mode-specific reasoning-effort profile when spawning subagents:

| Mode | Recon | Worker | Contract critic | Diff reviewer | Test auditor |
|---|---|---|---|---|---|
| quick/lite | medium | high | high | high | high |
| standard | high | high | xhigh | xhigh | xhigh |
| deep/strict | xhigh | xhigh | xhigh | xhigh | xhigh |

Pass the corresponding `reasoning_effort` override when the subagent tool supports it. Static custom agent TOML files are standard-mode defaults; the run mode still controls per-spawn overrides. Escalate individual agents above the table when a concrete risk warrants it, but do not downgrade an explicit user request for deeper reasoning.

Always consider these core dimensions:

- architecture and execution-path explorer;
- change-impact and compatibility explorer;
- test/build/quality explorer.

Add optional dimensions only when relevant:

- data/migration;
- security/auth/privacy;
- concurrency/performance;
- frontend/UX integration;
- infra/deployment;
- domain-specific reviewer;
- legacy/regression scout.

Recon dimensions may be role-based, subsystem-based, or both. Avoid launching duplicate general explorers merely to reach a target number.

When the user explicitly asks to analyze project modules, packages, subsystems, or "各个模块", first build a compact module map, then spawn module-oriented explorers for the relevant modules or module groups. Each module explorer must report that module's responsibilities, public interfaces, dependencies, invariants, tests, likely write boundaries, and contract clauses. Do not replace the later contract, ownership, worker, and combined-diff gates with a module summary.

Use custom agents from `.codex/agents/` when installed; otherwise use the built-in `explorer` agent with the prompts in `references/agent-prompts.md`.

Wait for all requested reports. Verify load-bearing claims in the repository before accepting them. Synthesize findings, contradictions, unknowns, and proposed contract clauses in the run directory.

### Phase 2: contract drafting and alignment

The main agent drafts `30-contract.md`. Read `references/contracts.md` before drafting.

The contract must define observable behavior, interfaces, invariants, compatibility, error semantics, ownership boundaries, acceptance checks, migration/rollback needs, and explicit non-goals.

Spawn at least one read-only contract critic. In `standard` and `strict` mode, also spawn a test/verification critic. Resolve every blocking criticism. Freeze the contract with:

```bash
python3 "$SKILL_DIR/scripts/freeze_contract.py" <run-directory>
```

Do not freeze a contract with unresolved blocking assumptions. Record non-blocking assumptions explicitly.

### Phase 3: work decomposition

Create `40-work-items.json`. Every item must include:

- stable id and goal;
- delegated agent type, usually `worker`;
- dependency ids;
- contract clauses implemented;
- read set, write set, and no-touch paths;
- acceptance commands;
- parallel group and intended integration order.

Reserve shared integration files—lockfiles, central registries, barrel exports, schemas, migrations, generated clients, and global configuration—for one owner, usually the main agent.

Validate the plan:

```bash
python3 "$SKILL_DIR/scripts/validate_run.py" <run-directory> --require-frozen
```

### Phase 4: bounded implementation

Choose one write strategy:

- **Shared checkout:** only for disjoint write sets and no shared generated outputs.
- **Isolated worktrees:** for overlapping domains or independently reviewable branches when worktree support is available.
- **Sequential worker delegation:** when isolation is unavailable, the repository is not Git-backed, or changes have shared side effects. Launch only one implementation worker at a time, but still delegate the work item to `worker` unless subagent tools are unavailable.

Before editing implementation code, spawn `worker` or an installed `implementation_worker` agent for each ready work item, limited by available thread capacity and write strategy. Use dependency waves rather than launching every item at once. If returning from a Plan-mode approval step, re-read the frozen contract and `40-work-items.json`, then start with worker delegation rather than main-agent edits.

Every worker prompt must include the exact contract version and hash, work-item id, allowed paths, forbidden paths, acceptance commands, and report schema. Workers must run the narrowest relevant checks and write a structured report to `50-worker-reports/`.

If any worker reports `CONTRACT_BREAK`, stop dependent work, revise and re-review the contract, increment its version, refreeze it, and reissue affected work items.

### Phase 5: combined-diff review and integration

After all workers finish:

1. Inspect the complete diff from the recorded base.
2. Run scope audit:

```bash
python3 "$SKILL_DIR/scripts/audit_diff_scope.py" <run-directory>
```

3. Spawn read-only reviewers against the combined diff, not isolated worker summaries. Cover correctness/regression and contract/API consistency; add tests/security/performance review when relevant.
4. Read `references/review-rubric.md` and validate each blocking finding yourself.
5. Make the smallest coherent integration fixes. Remove duplicate implementations, align interfaces, naming, error handling, tests, and generated artifacts.
6. If integration requires broad redesign or invalidates multiple work items, return to contract review instead of patching around the contract.

Do not enter combined-diff review or integration with only main-agent-authored implementation changes. At least one worker report must exist for each implemented work item, unless the user explicitly approved a direct fallback because subagent delegation was unavailable.

### Phase 6: validation

Run validation in widening order:

1. focused tests for each changed contract clause;
2. relevant type checks, lint, build, and package tests;
3. broader repository checks when feasible and required by the contract;
4. `git diff --check` and final working-tree inspection.

Distinguish pre-existing failures from introduced failures. Never claim full success when required checks did not run or failed.

Complete the acceptance matrix in `70-validation.md`. Every acceptance criterion needs concrete evidence: a command result, test, file/symbol inspection, or an explicitly stated limitation.

## Context protection

Keep only these items active in the main thread:

- compact task envelope;
- synthesized repository model;
- current contract version and hash;
- work-item status table;
- unresolved decisions;
- combined-diff summary;
- validation matrix.

Keep raw command output, exploratory notes, and verbose agent reports in subagent threads or run artifacts. Summaries should be decision-oriented and bounded.

## Final response

Report:

- outcome and user-visible behavior;
- frozen contract version;
- material files or modules changed;
- validation commands and results;
- contract deviations, unresolved risks, or skipped checks;
- run-artifact location when retained.

Do not present subagent consensus as proof. The main agent remains responsible for the final claim.
