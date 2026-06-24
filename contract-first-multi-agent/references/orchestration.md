# Orchestration runbook

## Contents

- State machine
- Mode selection
- Thread budget
- Baseline discipline
- Reconnaissance partitioning and evidence
- Write strategy and ownership
- Contract-break protocol
- Integration failure threshold

## State machine

| State | Main-agent action | Exit gate |
|---|---|---|
| INTAKE | Capture task, guidance, base, dirty state, constraints, and validation surface | G0 baseline recorded |
| RECON | Run read-only evidence gathering in parallel | G1 reports complete and evidence checked |
| SYNTHESIS | Build one repository model; reconcile contradictions | No unknown blocks safe planning |
| CONTRACT_REVIEW | Draft and criticize contract | G2 critics return ACCEPT or all blockers resolved |
| CONTRACT_FROZEN | Freeze version/hash; create ownership plan | Work items validate and dependencies are acyclic |
| IMPLEMENT | Run bounded write waves | G3 all items complete or explicitly blocked |
| DIFF_REVIEW | Review combined diff with independent read-only agents | Blocking findings verified and triaged |
| INTEGRATE | Main agent fixes cross-item inconsistencies | G4 diff conforms to contract |
| VALIDATE | Run acceptance matrix and widening checks | G5 required criteria have evidence |
| DONE | Summarize result and residual risk | Final claim is supportable |

Allowed backward transitions:

- `IMPLEMENT -> CONTRACT_REVIEW` on `CONTRACT_BREAK`.
- `DIFF_REVIEW -> CONTRACT_REVIEW` when the combined design violates the contract or requires broad redesign.
- `VALIDATE -> INTEGRATE` for a local introduced defect.
- `VALIDATE -> CONTRACT_REVIEW` when acceptance criteria or interface semantics were wrong.

Do not loop on cosmetic refinements. Stop when the contract is satisfied and required validation is complete.

## Mode selection

Default to `standard`. Recon agent count is not fixed; choose the smallest sufficient set based on task size, risk, and repository topology.

### Quick / Lite

Use when the change is bounded, low risk, and roughly one component or package.

- 2-3 reconnaissance agents.
- Reasoning effort: recon `medium`; implementation workers, contract critic, diff reviewer, and test auditor `high`.
- 1 contract critic.
- 1-2 implementation workers. Even a single implementation item should be delegated to a worker when subagent tools are available.
- 1 combined-diff reviewer.
- Focused validation plus repository-required checks.

### Standard

Use for cross-module features, meaningful refactors, or ambiguous bugs.

- 3-6 reconnaissance agents.
- Reasoning effort: recon and implementation workers `high`; contract critic, diff reviewer, and test auditor `xhigh`.
- 1 contract critic plus 1 verification critic.
- 2-4 workers in dependency waves.
- 2 combined-diff reviewers.
- Focused and package/repository validation.

### Deep / Strict

Use for public API changes, migrations, security-sensitive behavior, concurrency, persistence, authorization, payment/financial logic, or large refactors.

- 6-10 reconnaissance agents, launched in waves if needed.
- Reasoning effort: all reconnaissance, implementation, contract critic, diff reviewer, and test auditor agents `xhigh`.
- 2 independent contract critics.
- Worktrees or sequential writes unless ownership is provably disjoint.
- 2-3 combined-diff reviewers with distinct rubrics.
- Rollback/migration checks and broad validation.

Complexity indicators: multiple packages/services, public interface changes, data/schema migration, more than five likely files, unclear semantics, security/concurrency risk, or expensive rollback. Escalate mode when two or more indicators are present.

When spawning subagents, pass the mode-specific `reasoning_effort` override whenever the tool supports it. Treat static custom agent TOML values as standard-mode defaults, not as a reason to ignore the selected mode. Escalate an individual agent when its assigned dimension is unusually risky.

## Thread budget

Use waves. Never consume every available thread indefinitely.

- Keep one slot available for steering or targeted verification.
- Under the usual six-thread configuration, prefer no more than four simultaneous children. With larger thread budgets, still launch recon in purposeful waves rather than filling every slot.
- Close completed reconnaissance threads before contract review.
- Close completed implementation threads before combined-diff review.
- Keep child nesting at depth one.

## Baseline discipline

Record before edits:

- repository root;
- current branch and HEAD SHA;
- requested base ref and resolved SHA;
- `git status --short`;
- pre-existing changed paths and diff stat;
- known failing checks, when practical.

Do not modify or hide pre-existing user changes. If the task overlaps dirty files, prefer an isolated worktree based on a known commit. If that is unavailable, serialize changes and report the overlap explicitly.

## Reconnaissance partitioning

Default to partitioning by question, not arbitrary directory count. Always consider these core dimensions:

1. Architecture/execution path: call flow, module boundaries, public interfaces, and dependency direction.
2. Impact/compatibility: affected callers, backwards compatibility risks, API/schema/config implications.
3. Tests/validation: existing tests, missing coverage, commands, fixtures, and CI constraints.

Add optional dimensions only when relevant:

4. Data/migration: DB schema, migrations, backfills, serialization, and data compatibility.
5. Security/auth/privacy: permission checks, token handling, PII, and trust boundaries.
6. Concurrency/performance: races, retries, caching, batching, async behavior, and hot paths.
7. Frontend/UX integration: state management, API contracts, loading/error states, and accessibility.
8. Infra/deployment: env vars, feature flags, build system, generated clients, and release sequencing.
9. Domain-specific reviewer: payments, billing, search, ML, notifications, or another relevant domain.
10. Legacy/regression scout: old assumptions, implicit contracts, and brittle behavior.

When the user asks to analyze modules, packages, subsystems, or "各个模块", use a module-oriented reconnaissance pass:

1. Build a compact module map from repository evidence.
2. Select the modules or module groups that affect the requested change.
3. Spawn one read-only explorer per selected module or cohesive module group, within the thread budget.
4. Require each report to identify responsibilities, public interfaces, upstream/downstream dependencies, invariants, tests, risks, likely write boundaries, and suggested contract clauses.
5. Synthesize cross-module interface decisions before drafting the contract.

Recon dimensions may be role-based, subsystem-based, or both. Do not use module partitioning as permission for agents to write by module before the contract is frozen. Module reports feed the contract and work-item ownership plan.

Avoid duplicate general reviewers. Each report must contribute a different decision surface. Do not launch agents merely to hit the upper bound of a mode.

## Evidence rules

A material claim requires at least one of:

- file path plus symbol and line/range;
- command and summarized result;
- test name and observed behavior;
- versioned external documentation when repository behavior depends on it.

Classify confidence as high, medium, or low. Unknowns that affect interface or safety are blocking until resolved or explicitly accepted by the user.

## Write strategy selection

### Shared checkout

Use only when all conditions hold:

- exact write sets are disjoint;
- no worker runs formatters or generators that touch shared files;
- no worker modifies lockfiles, migrations, central exports, registries, or global config;
- workers can validate locally without mutating shared infrastructure.

### Isolated worktrees

Prefer when:

- agents may touch overlapping modules;
- each work item can produce an atomic commit;
- independent experimentation is useful;
- the Codex app or local Git workflow can provide one worktree per writer.

Main-agent integration order follows the dependency DAG. Workers must not merge each other.

### Sequential

Use when:

- the repository is not Git-backed;
- worktree isolation is unavailable;
- code generation or migrations create shared outputs;
- write ownership is uncertain;
- one item changes interfaces consumed by the next.

Parallel reading is still allowed. Sequential changes are still performed through one `worker` at a time when subagent tools are available. Sequential means "no concurrent writers"; it does not mean the main agent should implement work-item code directly.

Only allow main-agent direct implementation when subagent delegation is unavailable or the user explicitly asks for a direct patch after seeing the fallback tradeoff.

## Ownership rules

Represent ownership in `40-work-items.json`.

- A path may have one writer per parallel group.
- Directory globs must be narrow enough to avoid hidden overlap.
- Shared integration paths belong in `integration_owned` and are changed only by the main agent or one designated item.
- Dependencies must be explicit. An item may start only when all `depends_on` items are accepted.
- Workers may read outside their read set when needed for understanding, but may not write outside `write_set`.
- In Plan mode, each work item must name the intended delegated agent type, usually `worker`, so approval preserves the implementation delegation plan.

## Contract-break protocol

A worker returns `CONTRACT_BREAK` when it finds:

- an impossible or contradictory contract clause;
- an undocumented public-interface decision;
- a required change outside its ownership that alters another item's assumptions;
- an acceptance check that cannot prove the stated behavior;
- repository evidence that invalidates a frozen assumption.

On contract break:

1. stop dependent workers;
2. preserve completed, unaffected work;
3. main agent verifies the evidence;
4. revise contract and decision log;
5. rerun contract criticism on changed clauses;
6. increment version and hash;
7. update and reissue affected work items.

## Integration failure threshold

Treat integration as failed decomposition, not routine cleanup, when any condition holds:

- more than two worker domains require semantic rewrites;
- public interfaces must change after freeze;
- integration fixes are comparable in size to the worker implementation;
- duplicate approaches reveal conflicting architecture;
- validation exposes a missing acceptance criterion.

Return to contract review in these cases.
