---
name: sia-start
description: Set up SIA in a project and walk it from intake to execution. Use when the user says "start SIA", "set up SIA", "init SIA", "use SIA on this project", "sia status", or asks where SIA is in its workflow or why SIA refuses to prepare tasks.
---

# Starting SIA in a project

SIA keeps durable workflow state in `.sia/`. Work advances through
evidence-gated stages, and most orchestration commands only become legal at the
`execution` stage. This skill gets a project from nothing to there without the
user hitting a wall.

## How to call SIA

Use the **`sia` MCP server's tools** (`sia_doctor`, `sia_init`, `sia_next`,
`sia_advance`, …). The plugin starts that server itself; there is no
`pip install`, and Python 3 is the only prerequisite.

Every tool takes **`project_root`: the absolute path of the user's project.**
Never pass `.` or a relative path — the server runs from the plugin's own
directory, so a relative path would point at the plugin, and SIA rejects it.

If the `sia_*` tools are not available in this host, fall back to the bundled
CLI, run from the project root:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" <command>
```

If neither works, say plainly that SIA is not reachable and stop. Do not try to
install Python or SIA.

## Step 1 — look before initializing

Call `sia_doctor`. It is read-only and works before `init`: it reports whether
`.sia/` exists, whether the workflow policy is complete, and which other agent
frameworks are present.

If `.sia/` already exists, do NOT re-initialize. Call `sia_status` and
`sia_next`, and continue from wherever the project actually is.

## Step 2 — choose a mode deliberately

The mode decides which stages exist, and it is persisted.

| Mode | Stages | Choose when |
|---|---|---|
| `advisory` | feedback | Another framework owns the whole workflow; SIA only captures rules and convergence |
| `planning` | intake -> plan | Another framework owns execution; SIA plans |
| `orchestrator` | intake -> feedback, including execution | SIA should dispatch subagents and own integration |

Only `orchestrator` can prepare tasks or dispatch workers. If the user wants
SIA to run subagents it must be `orchestrator` — anything else refuses later,
and the refusal will look like a bug.

Ask which mode the user wants unless they already said, then call `sia_init`
with that `mode`. `init` never overwrites a root `AGENT.md`, `AGENTS.md` or
`CLAUDE.md`, and records detected frameworks under `bridge` policy so they keep
working.

## Step 3 — walk the stages, do not skip them

This is what makes SIA look broken when it is skipped. After `init` the project
sits at `intake`. Task preparation and dispatch planning refuse until
`execution`. In orchestrator mode that is five advances:

```
intake -> spec -> project-instructions -> skills -> plan -> execution
```

For each stage: call `sia_next` to learn what it requires, do that work, write
the artifact to disk, then call `sia_advance` with `evidence` listing its
project-relative path.

Work each stage properly rather than manufacturing a file to satisfy the gate.
A claim in conversation is never evidence — only a path is.

If the user wants to skip planning for a small change, say plainly that SIA's
gates are the product, and offer `advisory` mode instead, which does not pretend
to plan.

## Step 4 — confirm arrival

Call `sia_status`. When `current_stage` is `execution`, hand off to the
`sia-orchestrate` skill.

## Reading a refusal

Refusals name the remedy. *"preparing tasks is only available at the
'execution' stage; this project is at 'intake'"* means the stages have not been
walked, not that anything is broken. Call `sia_next` and continue from there.

## What not to do

- Do not create or edit `.sia/` files by hand. SIA owns that directory.
- Do not edit `.sia/state.json` to jump a stage. The gates are the point.
- Do not re-initialize a project to "reset" it without saying what will be lost.
- Do not replace a competing framework's files. SIA coexists by design.
