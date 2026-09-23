---
name: sia-workflow
description: SIA's workflow contract — evidence-gated stages, file-ownership safety, receipt and telemetry honesty, feedback rules and convergence. Use when working in a project that has a .sia/ directory, when recording a PASS or DEVIATION, when running preflight or convergence, or when deciding whether SIA or another framework owns a stage.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# The SIA workflow contract

Load this when a project has a `.sia/` directory. It describes the rules SIA
enforces and why, so they are followed rather than worked around.

Run the bundled CLI with `python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" <command>`.

## Evidence over assertion

Every stage transition requires a path to an artifact that exists. A claim in
conversation is never evidence. This is the core idea: it is what stops an
agent declaring work done because it believes it is done.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" next --json      # authoritative position
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" advance --evidence <path>
```

Treat the `next --json` packet as the truth about where the project is, over
anything remembered from earlier in a conversation. That is what makes SIA
survive a new chat.

## Stages

`intake -> spec -> project-instructions -> skills -> plan -> execution -> feedback`

Narrower modes have fewer stages: `planning` stops after `plan`; `advisory` has
only `feedback`. The mode is persisted at `init` and decides what is legal.

## Ownership, and the controller's restraint

In execution, every task declares the exact files it owns, and **no two tasks
share a file**. The controller briefs, dispatches, reviews and integrates — it
does not implement task-owned files itself. A reviewer is never the agent that
wrote the code.

These are not ceremony. Shared ownership yields conflicting edits discovered
late; a self-reviewing agent reliably approves its own work.

## Telemetry honesty

SIA labels every figure by provenance:

| Label | Means |
|---|---|
| `actual` | The provider or worker reported it |
| `calculated` | Actual tokens multiplied by configured prices |
| `estimated` | SIA's own heuristic |
| `unknown` | Not exposed — and left that way |

Hosts differ in what they expose. When a value is unavailable, record `null`
or `unknown`. Never substitute a plausible number: a fabricated token count
corrupts budget reservations, routing decisions and convergence at once, and
does so invisibly.

## Coexistence

The default `bridge` policy detects frameworks such as BMAD, Superpowers and
host config directories, records them in `.sia/config.json`, and never replaces
a root `AGENT.md`, `AGENTS.md` or `CLAUDE.md`.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" owner --stage plan --to bmad
```

If another framework owns execution, SIA emits a handoff and launches nothing.
Respect that — do not dispatch workers behind another owner's back.

## Feedback, rules and convergence

Outcomes are recorded, not remembered:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" record --outcome pass --context "<what held>"
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" capture --signal deviation \
  --error-class <class> --context "<what went wrong>"
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" rule add --text "<standing rule>" --source <evidence>
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" preflight      # before proposing work
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" convergence    # deviation rate per class
```

Run `preflight` before proposing new work so prior corrections actually apply.
A rule carries its provenance: the deviation that produced it. A rule with no
evidence behind it is an opinion, and SIA does not store opinions.

Falling deviation rates per error class are the signal that the loop is
working. A class that never converges is a signal the rule is wrong, not that
the agent needs more discipline.

## Where state lives

```
.sia/config.json     mode, framework policy, stage owners, orchestration
.sia/state.json      current stage, completed stages, tasks
.sia/events.jsonl    append-only outcome log
.sia/rules.json      provenance-bearing feedback rules
.sia/runs/<run-id>/  briefs, reports, reviews, receipts, integration
```

The CLI owns this directory. Do not hand-edit it — particularly not
`state.json` to skip a gate.
