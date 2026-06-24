# Contract-First Multi-Agent Skill

Codex skill for medium-to-large code changes that need parallel reconnaissance, a frozen implementation contract, bounded worker agents, combined-diff review, and main-agent integration.

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

The workflow:

1. Inspect repository guidance and record the baseline.
2. Spawn read-only reconnaissance agents.
3. Draft, critique, and freeze an implementation contract.
4. Decompose work into bounded worker items with explicit write sets.
5. Implement through worker subagents, not direct main-agent edits.
6. Review the complete base-to-working-tree diff.
7. Integrate, validate, and report residual risk.

## Modes

Recon agent count and reasoning depth scale with mode:

| Mode | Recon count | Recon | Worker | Contract critic | Diff reviewer | Test auditor |
|---|---:|---|---|---|---|---|
| quick/lite | 2-3 | medium | high | high | high | high |
| standard | 3-6 | high | high | xhigh | xhigh | xhigh |
| deep/strict | 6-10 | xhigh | xhigh | xhigh | xhigh | xhigh |

The main agent chooses the smallest sufficient reconnaissance set based on task size, risk, and repository topology.

## Included

- `SKILL.md`: core workflow and hard gates.
- `references/`: orchestration, contract, prompts, review rubric, and recovery instructions.
- `scripts/`: deterministic run initialization, contract freezing, run validation, and diff-scope audit.
- `assets/run/`: workflow artifact templates.
- `assets/custom-agents/`: optional custom agent TOML templates.
