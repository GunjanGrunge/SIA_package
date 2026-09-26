---
name: sia-orchestrate
description: Configure model tiers and dispatch SIA subagents with budgets, file-ownership safety and independent review. Use when the user says "sia orchestrate", "dispatch SIA agents", "run SIA workers", "configure SIA models", or asks SIA to parallelize implementation work across cheap and strong models.
---

# Orchestrating work with SIA

SIA turns approved plan work into an immutable dispatch plan: each operation
owns an exact file set, routes to an explicitly configured model tier, reserves
budget, and must be independently reviewed before integration.

Call the **`sia` MCP server's tools**. Every tool takes `project_root`: the
**absolute** path of the user's project. Relative paths in other arguments
resolve against that root. If the `sia_*` tools are unavailable, fall back to
`python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" <command>` from the project root.

## Prerequisite

Orchestration is only legal in `orchestrator` mode at the `execution` stage. If
a tool refuses, read the message: it names the current stage and the remaining
advances. Use the `sia-start` skill to get there. Do not work around the gate.

## Working alongside other frameworks

`sia_doctor` lists frameworks it finds, including ones installed as plugins
(e.g. `superpowers`). When one is present, compose with it instead of
duplicating it:

- **Spec and plan:** use its skills to *author* the artifacts SIA's stages need
  (Superpowers' brainstorming for the spec, writing-plans for the plan). SIA
  still gates on them: advance with the written file as evidence.
- **Execution:** SIA is the **one** dispatcher. Do not also run another
  framework's subagent-dispatch or plan-execution skill for the same work;
  two dispatchers would do everything twice and break file ownership.
- **Inside each task:** subagents may and should use installed practice skills
  (test-driven development, systematic debugging, verification). The
  `sia-implementer` and `sia-reviewer` agents are told to.

Every subagent, whoever spawns it, automatically receives the project's learned
rules when it starts, so corrections the user made earlier are not repeated.

## Step 1 — configure model tiers

Every operation routes to one of three tiers the user must name explicitly.
SIA never guesses which model the host has selected.

Call `sia_orchestrate_example`, and write the JSON it returns to a file in the
project, e.g. `orchestration.json`. It contains `replace-with-*` placeholders.
**Ask the user for real model IDs and prices** — do not invent them.
`sia_orchestrate_configure` rejects any placeholder left in.

- `cheap` — bounded scans, routine tests, docs, low-risk simple work
- `current` — normal implementation and review
- `strong` — high-risk, security, architecture, complex escalation

**This is where the cost saving comes from**, so use IDs the host can actually
run a subagent on. In Claude Code the subagent tool accepts the aliases
`haiku`, `sonnet` and `opus`, so a sensible default to offer the user is
`cheap: haiku`, `current: sonnet`, `strong: opus`. In other hosts, ask which
models their subagents can use.

Prices are per million tokens and may be `0`, which disables cost estimation but
keeps token budgets working. Then call `sia_orchestrate_configure` with
`file: "orchestration.json"`.

## Step 2 — prepare tasks with exact ownership

Call `sia_task_prepare` once per task, with `task`, `brief`, `files`, and
optionally `risk`, `complexity` and `estimated_tokens`.

**No two tasks may share a file.** This invariant is what makes parallel
dispatch safe; overlapping ownership produces conflicting edits that only
surface at integration. Decide ownership before dispatching, not after.

Risk and complexity drive routing: low/simple to `cheap`, normal to `current`,
high/complex to `strong`, reviews to `current` except high-risk reviews.

## Step 3 — plan the dispatch

Call `sia_orchestrate_plan` with `backend: "native-host"` and `host` set to this
host (`claude`, `codex`, `gemini`, `kiro`, `antigravity`). Then
`sia_orchestrate_status`.

Planning reserves the whole estimated budget and refuses a plan above either
hard ceiling. The plan is immutable, and every receipt must cite its ID and
hash.

`backend: "standalone"` makes SIA launch configured provider CLIs itself. Its
execution step is deliberately **not** available as a tool: it requires a human
to run `sia orchestrate run --approve-commands` from a terminal. Never try to
work around that.

## Step 4 — dispatch, as the controller

Launch every ready implementer **in parallel** with this host's subagent tool,
using the `sia-implementer` agent where the host supports named agents.

**Pass each operation's `requested_model_id` as the subagent's model** (in
Claude Code, the subagent tool's `model` parameter). Skipping this runs every
subagent on the expensive default and throws the cost saving away: the plan's
routing only matters if the spawn honours it. Record the model the subagent
actually ran on in its receipt.

The controller must not edit task-owned files itself. Brief, dispatch, review,
integrate, escalate — that separation is what makes the review independent.

Give each worker its brief path, its exact owned files, and the instruction to
write a non-empty report.

## Step 5 — ingest receipts truthfully

After each worker, write a receipt JSON file **outside `.sia/`** — for example
`sdd/receipts/<operation>.json` — and call `sia_orchestrate_receipt` with its
path. SIA stores its own canonical copy inside `.sia/`; never write or edit files
there yourself. A receipt cites the plan ID and hash, the operation ID, agent
identity, requested and actual model, the report path, and usage.

**Never fabricate telemetry.** If the host did not expose the actual model or
token usage, set `actual_model_id` to `null` and leave telemetry empty — SIA
then labels the figure `estimated` rather than `actual`. An invented number
silently corrupts every budget decision that follows.

## Step 6 — review, then integrate

Launch reviewers with the `sia-reviewer` agent only after implementers complete.
A reviewer's agent ID must differ from the implementer's; SIA rejects
self-review.

Call `sia_orchestrate_status`. Only when it reports `complete`, call
`sia_integration` with the combined-validation evidence. Integration means the
whole combined diff was validated as one unit — not that each task passed its
own check in isolation.

## Budget stops

An overrun is terminal: later receipts are rejected and integration is blocked.
Record it rather than raising the ceiling reflexively — call `sia_capture` with
`signal: "budget-overrun"`, `severity: "high"`, `error_class: "cost-overrun"`,
and a `context` saying what overran and why.
