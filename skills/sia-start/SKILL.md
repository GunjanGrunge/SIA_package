---
name: sia-start
description: Set up SIA in a project and walk it from intake to execution. Use when the user says "start SIA", "set up SIA", "init SIA", "use SIA on this project", "sia status", or asks where SIA is in its workflow or why SIA refuses to prepare tasks.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Starting SIA in a project

SIA keeps durable workflow state in `.sia/`. Work advances through
evidence-gated stages, and most orchestration commands only become legal at the
`execution` stage. This skill gets a project from nothing to there without the
user hitting a wall.

## Running the CLI

The CLI is bundled with the plugin. There is no `pip install`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" <command>
```

Use `python` instead of `python3` if `python3` is unavailable. Always run from
the project root — SIA resolves `.sia/` relative to the working directory.

Verify once before anything else:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" --version
```

If Python is missing, say so plainly and stop. Do not attempt to install it.

## Step 1 — look before initializing

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" doctor
```

`doctor` is read-only and works before `init`. It reports whether `.sia/`
exists, whether the workflow policy is complete, and which competing frameworks
are present.

If `.sia/` already exists, do NOT re-initialize. Run `status` and `next`, then
continue from wherever the project actually is.

## Step 2 — choose a mode deliberately

The mode decides which stages exist, and it is persisted.

| Mode | Stages | Choose when |
|---|---|---|
| `advisory` | feedback | Another framework owns the whole workflow; SIA only captures rules and convergence |
| `planning` | intake -> plan | Another framework owns execution; SIA plans |
| `orchestrator` | intake -> feedback, including execution | SIA should dispatch subagents and own integration |

Only `orchestrator` can prepare tasks or dispatch workers. If the user wants
SIA to run subagents, it must be `orchestrator` — anything else will refuse
later, and the refusal will look like a bug.

Ask which mode the user wants unless they already said. Then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" init --mode orchestrator
```

`init` never overwrites a root `AGENT.md`, `AGENTS.md` or `CLAUDE.md`, and it
records detected frameworks under `bridge` policy so they keep working.

## Step 3 — walk the stages, do not skip them

This is the part that makes SIA look broken when it is skipped. After `init`
the project sits at `intake`. `task prepare` and `orchestrate plan` refuse
until `execution`. In orchestrator mode that is five advances:

```
intake -> spec -> project-instructions -> skills -> plan -> execution
```

Each advance requires real evidence on disk:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" next --json
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" advance --evidence <path>
```

Work each stage properly rather than manufacturing a file to satisfy the gate.
`next --json` states the required action for the current stage; do that work,
write the artifact, then advance citing it. A conversation claim is not
evidence — only a path is.

If the user explicitly wants to skip planning for a small change, say plainly
that SIA's gates are the product, and offer `advisory` mode instead, which does
not pretend to plan.

## Step 4 — confirm arrival

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" status
```

When `current_stage` is `execution`, hand off to the `sia-orchestrate` skill.

## Reading a refusal

Refusals name the remedy. `preparing tasks is only available at the 'execution'
stage; this project is at 'intake'` means the stages have not been walked, not
that anything is broken. Run `next --json` and continue from there.

## What not to do

- Do not create `.sia/` files by hand. The CLI owns that directory.
- Do not edit `.sia/state.json` to jump a stage. The gates are the point.
- Do not re-run `init` to "reset" a project without saying what will be lost.
- Do not replace a competing framework's files. SIA coexists by design.
