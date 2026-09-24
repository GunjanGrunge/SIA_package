---
name: sia-workflow
description: SIA's workflow contract — evidence-gated stages, file-ownership safety, receipt and telemetry honesty, feedback rules and convergence. Use when working in a project that has a .sia/ directory, when recording a PASS or DEVIATION, when running preflight or convergence, or when deciding whether SIA or another framework owns a stage.
---

# The SIA workflow contract

Load this when a project has a `.sia/` directory. It describes the rules SIA
enforces and why, so they are followed rather than worked around.

Call the **`sia` MCP server's tools**, always passing `project_root` as the
**absolute** path of the project. If they are unavailable, fall back to
`python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" <command>` from the project root.

## Evidence over assertion

Every stage transition requires a path to an artifact that exists. A claim in
conversation is never evidence. This is the core idea: it is what stops an
agent declaring work done because it believes it is done.

Call `sia_next` for the authoritative position, and `sia_advance` with
`evidence` paths to move on. Treat the `sia_next` packet as the truth about
where the project is, over anything remembered from earlier in a conversation.
That is what lets SIA survive a new chat.

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

Hosts differ in what they expose. When a value is unavailable, record `null` or
`unknown`. Never substitute a plausible number: a fabricated token count
corrupts budget reservations, routing decisions and convergence at once, and
does so invisibly.

## Coexistence

The default `bridge` policy detects frameworks such as BMAD, Superpowers and
host config directories, records them in `.sia/config.json`, and never replaces
a root `AGENT.md`, `AGENTS.md` or `CLAUDE.md`.

To hand a stage to another framework, call `sia_owner` with `stage` and `to`
(e.g. `stage: "plan"`, `to: "bmad"`). If another framework owns execution, SIA
emits a handoff and launches nothing. Respect that — do not dispatch workers
behind another owner's back.

## Feedback, rules and convergence

Outcomes are recorded, not remembered.

- **`sia_preflight`** with `scope` (the files or globs about to be touched) —
  run it *before* proposing work so prior corrections actually apply.
- **`sia_record`** with `outcome` (`pass`/`deviation`), `signal`, `context` and
  `severity`; add `error_class` for a deviation.
- **`sia_capture`** for a deviation, with `signal`, `context`, `severity` and
  `error_class`.
- **`sia_convergence`** — deviation rate per error class.

Standing rules are added from the CLI, because each one must cite the event that
produced it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" rule add --text "<standing rule>" \
  --scope "<glob>" --severity medium --error-class <class> --source-event <event-id>
```

A rule with no evidence behind it is an opinion, and SIA does not store
opinions. Falling deviation rates per error class mean the loop is working. A
class that never converges means the rule is wrong, not that the agent needs
more discipline.

## Where state lives

```
.sia/config.json     mode, framework policy, stage owners, orchestration
.sia/state.json      current stage, completed stages, tasks
.sia/events.jsonl    append-only outcome log
.sia/rules.json      provenance-bearing feedback rules
.sia/runs/<run-id>/  briefs, reports, reviews, receipts, integration
```

SIA owns this directory. Do not hand-edit it — particularly not `state.json` to
skip a gate.
