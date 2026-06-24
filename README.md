# Contract-First Multi-Agent Skill

A Codex skill for complex code changes where a single main agent should not
explore everything, design everything, implement everything, and review itself
in one uninterrupted thread.

This skill turns a large coding task into a controlled multi-agent workflow:

- read-only subagents inspect the repository from different angles;
- the main agent writes and freezes an implementation contract;
- worker subagents implement bounded work items against that contract;
- independent reviewers inspect the complete combined diff;
- the main agent integrates, validates, and owns the final result.

The core idea is simple: **parallelize evidence gathering and bounded
implementation, but keep architectural decisions and final integration
centralized.**

## Why Use It

Large repository changes often fail in predictable ways:

- the main thread fills up with search output and test logs;
- different agents invent incompatible interfaces;
- workers touch overlapping files or shared generated artifacts;
- implementation starts before behavior and acceptance criteria are clear;
- final review checks only worker summaries instead of the whole diff;
- Plan mode produces a good-looking plan, then the main agent implements it
  alone.

This skill is designed to prevent those failure modes. It forces a contract
gate before implementation, explicit write ownership for every worker, and a
combined-diff review before final validation.

## When To Use

Use this skill for:

- cross-module features;
- medium or large refactors;
- migrations or schema/config changes;
- risky bug fixes with unclear blast radius;
- codebase work that benefits from multiple reconnaissance agents;
- explicit multi-agent implementation workflows.

Do not use it for:

- tiny one-file edits;
- direct fast patches where the overhead is larger than the change;
- tasks where the user explicitly wants the main agent to make the edit
  immediately.

## Workflow

The workflow follows a fixed set of gates:

```text
INTAKE
  -> RECON
  -> SYNTHESIS
  -> CONTRACT_REVIEW
  -> CONTRACT_FROZEN
  -> IMPLEMENT
  -> DIFF_REVIEW
  -> INTEGRATE
  -> VALIDATE
  -> DONE
```

### 1. Reconnaissance

The main agent chooses the smallest sufficient set of read-only reconnaissance
agents based on task size, risk, and repository topology.

Core dimensions:

- architecture / execution path;
- impact / compatibility;
- tests / validation.

Optional dimensions are added only when relevant:

- data / migration;
- security / auth / privacy;
- concurrency / performance;
- frontend / UX integration;
- infra / deployment;
- domain-specific review;
- legacy / regression scouting.

If the user asks to analyze modules or packages, the skill first builds a
module map and then assigns module-oriented explorers.

### 2. Implementation Contract

The main agent drafts `30-contract.md`, then contract critics review it before
implementation is allowed.

The contract captures:

- target behavior and non-goals;
- public interfaces and data contracts;
- invariants and compatibility rules;
- error, logging, observability, security, concurrency, and performance
  semantics;
- acceptance criteria and validation plan;
- ownership boundaries and rollback or recovery.

Implementation cannot start until the contract is marked `FROZEN` and hashed.

### 3. Work Items

The main agent creates `40-work-items.json`. Each work item must define:

- contract version and hash;
- delegated agent type;
- dependencies;
- read set and write set;
- no-touch paths;
- acceptance commands;
- parallel group and integration order.

Workers may read broadly, but they may write only inside their assigned write
set.

### 4. Worker Implementation

Worker subagents implement bounded work items against the frozen contract.

If a worker discovers that the contract is wrong or incomplete, it must return
`CONTRACT_BREAK` instead of inventing a new interface.

Sequential mode still means sequential worker delegation. It does not mean the
main agent should directly implement work-item code unless subagent delegation
is unavailable and the user approves that fallback.

### 5. Combined-Diff Review

After workers finish, reviewers inspect the full base-to-working-tree diff.

Review focuses on:

- interface and type consistency;
- duplicated or competing logic;
- naming and error semantics;
- compatibility and migration behavior;
- test coverage and validation evidence;
- out-of-scope changes and write-boundary violations.

The main agent verifies reviewer findings, makes integration fixes, and runs
the final validation matrix.

## Modes

Recon agent count and reasoning effort scale by mode.

| Mode | Recon count | Recon | Worker | Contract critic | Diff reviewer | Test auditor |
|---|---:|---|---|---|---|---|
| quick/lite | 2-3 | medium | high | high | high | high |
| standard | 3-6 | high | high | xhigh | xhigh | xhigh |
| deep/strict | 6-10 | xhigh | xhigh | xhigh | xhigh | xhigh |

`quick` and `lite` are equivalent. `deep` and `strict` are equivalent.

The main agent should not launch agents just to reach the upper bound. The
right number is the smallest set that gives enough evidence to write a safe
contract.

## Plan Mode Behavior

This skill is intentionally strict in plan-first workflows.

If Codex is operating in Plan mode, a valid implementation plan must include:

- selected mode and write strategy;
- reasoning-effort profile;
- reconnaissance agents or module map when relevant;
- contract-freeze gate;
- worker waves with work-item ids, dependencies, write sets, no-touch paths,
  acceptance commands, and delegated `worker` execution;
- main-agent-owned integration paths and final validation.

A plan that only lists files for the main agent to edit is not a valid plan for
this skill.

## Install

Copy the skill folder into your Codex skills directory:

```powershell
Copy-Item -Recurse .\contract-first-multi-agent "$env:USERPROFILE\.codex\skills\"
```

Optional custom agent templates:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\agents"
Copy-Item .\contract-first-multi-agent\assets\custom-agents\*.toml "$env:USERPROFILE\.codex\agents\"
```

Restart Codex after installing.

## Usage

Invoke the skill explicitly:

```text
$contract-first-multi-agent <your coding task>
```

Example:

```text
$contract-first-multi-agent Analyze each major module of this repository, then
create a contract-first multi-agent implementation plan. Freeze the contract
before code changes. Implement through worker subagents with disjoint write
sets. After implementation, review the complete diff for interface consistency,
duplicate logic, naming, error handling, and test coverage.
```

## Repository Layout

- `contract-first-multi-agent/SKILL.md`: core workflow and hard gates.
- `contract-first-multi-agent/references/`: orchestration, contract schema,
  prompt library, review rubric, and recovery playbook.
- `contract-first-multi-agent/scripts/`: deterministic helpers for run
  initialization, contract freezing, workflow validation, and diff-scope audit.
- `contract-first-multi-agent/assets/run/`: workflow artifact templates.
- `contract-first-multi-agent/assets/custom-agents/`: optional custom agent
  TOML templates.
