# Combined-diff review and integration rubric

## Evidence threshold

A review finding is actionable only when it includes:

- a concrete affected path and symbol/line;
- a plausible execution or failure path;
- the violated contract clause or repository invariant;
- impact and confidence;
- a fix direction small enough to assess.

The main agent verifies blocker/high findings before changing code. Reject speculative, duplicate, or style-only findings.

## Severity

- **BLOCKER:** data loss, security boundary failure, build unusable, public contract fundamentally wrong, or acceptance cannot be met.
- **HIGH:** likely user-visible regression, incorrect state transition, race, incompatible API/schema change, or important missing negative path.
- **MEDIUM:** bounded defect, maintainability issue likely to create near-term errors, incomplete observability, or missing non-critical test.
- **LOW:** minor risk or consistency issue. Do not expand scope solely to fix low findings.

## Review dimensions

### Contract compliance

- Each target behavior and acceptance criterion is implemented.
- No code silently changes a frozen interface, schema, error, or compatibility rule.
- Non-goals remain untouched.
- Assumptions are still true.

### Cross-module consistency

- Producer and consumer types/signatures agree.
- Naming, error taxonomy, retries, logging, and null/optional semantics agree.
- Shared constants and helpers are not duplicated.
- Generated artifacts correspond to source changes.
- Migration and runtime ordering are valid.

### Correctness and regression

- Happy, negative, edge, and partial-failure paths are coherent.
- State is not partially committed on failure.
- Authorization and trust boundaries remain enforced.
- Concurrency, idempotency, retry, and timeout behavior are safe where relevant.
- Existing callers continue to work or have an explicit migration.

### Tests and validation

- Tests assert observable behavior rather than implementation trivia.
- Acceptance criteria map to concrete checks.
- Negative paths and regressions are covered.
- Mocks/fixtures reflect real interfaces.
- Broad checks do not hide focused failures.

### Diff hygiene

- No unrelated formatting or generated churn.
- No debug artifacts, temporary code, stale comments, or dead branches.
- No accidental lockfile/config changes.
- No worker writes outside declared scope.
- The diff is understandable as one coherent change.

## Main-agent integration pass

The main agent should:

1. build a contract-compliance matrix;
2. reconcile reviewer findings and remove duplicates;
3. inspect every public or shared interface directly;
4. choose one implementation when workers produced competing abstractions;
5. centralize shared logic only when required by the contract;
6. make minimal fixes in dependency order;
7. rerun focused tests after each semantic integration fix;
8. rerun combined validation after the integration pass.

Do not perform a broad cleanup or opportunistic refactor during integration.

## Escalation rule

Return to contract review instead of continuing integration when:

- a public interface must change;
- multiple work items need semantic rewrites;
- the acceptance plan was insufficient;
- ownership boundaries caused widespread duplication;
- integration fixes approach the size or complexity of implementation work.
