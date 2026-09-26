---
name: sia-workflow
description: SIA's workflow contract — learning standing rules from the user's corrections, evidence-gated stages, file-ownership safety, telemetry honesty, and convergence. Use when the user corrects your work or states a lasting preference ("don't do X", "always Y", "that's too long", "call it Z"), when working in a project that has a .sia/ directory, when recording a PASS or DEVIATION, when running preflight or convergence, or when deciding whether SIA or another framework owns a stage.
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

## Learning from the user

**Whenever the user corrects your work or states a lasting preference for this
project, call `sia_rule_learn` straight away**, before carrying on. This is how
SIA learns. Anything counts, for example:

- "don't use em dashes" / "stop saying *leverage*"
- "your answers are too long" / "use British spelling"
- "always write the test first" / "never touch `infra/` without asking me"
- "call it a *stash*, not a *drive*"

Pass `text` (the rule, phrased as an instruction) and `user_quote` (their exact
words, kept as evidence). Leave `scope` as `**` unless the preference is about
particular files, e.g. `infra/**`.

**One call per preference.** If the user states three preferences at once, make
three calls, each with its own `text`, `user_quote` and (where it applies)
`forbid`. A merged rule cannot be retired in part: when the user later says
"em dashes are fine now", retiring a combined rule would silently drop the
others too.

Only if the rule is **mechanical** — a banned character, word or phrase — also
pass `forbid` as a regex (`—` for em dashes, `\\bleverage\\b`). SIA then checks
every file you write and every reply, and pushes back on a violation. Most
preferences are not mechanical ("keep it short"); omit `forbid` for those.

Every active rule is loaded into each new session automatically, so you do not
need to re-ask. If a rule is pushed back to you as violated, fix the output and
carry on; do not argue with the rule. If the user says a rule no longer applies,
retire it with `sia_rule_retire`.

When you tell the user you changed something to follow a rule, describe it
without repeating the banned text ("I dropped a word the project avoids").
Quoting it trips the same check on your reply.

Do not invent rules the user did not state, and do not record one-off
instructions ("make this button blue") as standing rules. A rule is for
something they want to hold from now on.

## Feedback, rules and convergence

Outcomes are recorded, not remembered.

- **`sia_preflight`** with `scope` (the files or globs about to be touched) —
  run it *before* proposing work so prior corrections actually apply.
- **`sia_record`** with `outcome` (`pass`/`deviation`), `signal`, `context` and
  `severity`; add `error_class` for a deviation.
- **`sia_capture`** for a deviation, with `signal`, `context`, `severity` and
  `error_class`.
- **`sia_convergence`** — deviation rate per error class.

A rule with no evidence behind it is an opinion, and SIA does not store
opinions — which is why `sia_rule_learn` keeps the user's own words. Falling deviation rates per error class mean the loop is working. A
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
