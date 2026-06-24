# Recovery and safety playbook

## Dirty working tree

- Record all pre-existing changed paths and diff stat.
- Never run `git reset --hard`, `git clean`, or automatic stash.
- If task files overlap user changes, prefer a clean worktree from the recorded commit.
- If isolation is unavailable, serialize changes, preserve the existing diff, and call out the overlap in the final report.

## Agent writes outside scope

- Stop that agent.
- Record the unexpected paths.
- Do not discard user work blindly.
- Main agent inspects the diff, reverts only clearly workflow-generated out-of-scope hunks when safe, and narrows the prompt.
- Mark the worker report invalid and rerun or absorb the work sequentially.

## Concurrent edit conflict

- Pause the affected wave.
- Determine ownership from `40-work-items.json`.
- Keep the designated owner's implementation; do not merge two semantic approaches automatically.
- Move the shared path to `integration_owned` or serialize the items.
- Revalidate dependencies before resuming.

## Contract break

- Verify the worker's evidence.
- Change status to `DRAFT`.
- Add a decision-log entry.
- Revise only affected clauses.
- Re-run contract criticism.
- Increment version/hash and invalidate affected old reports.

## Failing validation

Classify first:

- pre-existing;
- introduced by current diff;
- environmental/tooling;
- flaky;
- evidence of an invalid contract.

Use a read-only failure analyst for complex logs. Fix introduced defects in `INTEGRATE`; revisit the contract when semantics or acceptance criteria are wrong. Never label an unrun or failed required check as passed.

## Resource pressure

When token, time, or thread budget is constrained:

1. reduce duplicate reconnaissance, not contract quality;
2. close completed agents;
3. serialize workers rather than weakening ownership;
4. run focused validation first;
5. state skipped broad checks and residual risk explicitly.

## Non-Git repositories

Use the same read/contract/review workflow, but choose sequential writes. Capture a filesystem baseline using available tooling and avoid destructive cleanup.
