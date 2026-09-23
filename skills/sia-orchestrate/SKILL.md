---
name: sia-orchestrate
description: Configure model tiers and dispatch SIA subagents with budgets, file-ownership safety and independent review. Use when the user says "sia orchestrate", "dispatch SIA agents", "run SIA workers", "configure SIA models", or asks SIA to parallelize implementation work across cheap and strong models.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task
---

# Orchestrating work with SIA

SIA turns approved plan work into an immutable dispatch plan: each operation
owns an exact file set, routes to an explicitly configured model tier, reserves
budget, and must be independently reviewed before integration.

Run the bundled CLI — no `pip install`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" <command>
```

## Prerequisite

Orchestration is only legal in `orchestrator` mode at the `execution` stage. If
a command refuses, read the message: it names the current stage and the
remaining advances. Use the `sia-start` skill to get there. Do not work around
the gate.

## Step 1 — configure model tiers

Every operation routes to one of three tiers the user must name explicitly.
SIA never guesses which model the host has selected.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" orchestrate example > orchestration.json
```

The generated file contains `replace-with-*` placeholders. **Ask the user for
real model IDs and prices** — do not invent them, and do not leave the
placeholders, which `configure` now rejects outright.

- `cheap` — bounded scans, routine tests, docs, low-risk simple work
- `current` — normal implementation and review
- `strong` — high-risk, security, architecture, complex escalation

Prices are per million tokens and may be `0`, which disables cost estimation
but keeps token budgets working. Then:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" orchestrate configure --file orchestration.json
```

## Step 2 — prepare tasks with exact ownership

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" task prepare --task auth --brief sdd/auth.md \
  --files src/auth.py --risk high --complexity complex --estimated-tokens 40000
```

**No two tasks may share a file.** This is the invariant that makes parallel
dispatch safe; overlapping ownership produces conflicting edits that only
surface at integration. Decide ownership before dispatching, not after.

Risk and complexity drive routing: low/simple to `cheap`, normal to `current`,
high/complex to `strong`, reviews to `current` except high-risk reviews.

## Step 3 — plan the dispatch

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" orchestrate plan --backend native-host --host claude
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" orchestrate status
```

Planning reserves the whole estimated budget under a project lock and refuses a
plan above either hard ceiling. The plan is immutable and carries an ID and
hash that every receipt must cite.

Choose the backend deliberately:

- **`native-host`** — this Claude Code session spawns the workers with the
  subagent-dispatch tool. Use this by default.
- **`standalone`** — SIA launches configured provider CLIs itself with
  `shell=False`, gated behind `orchestrate run --approve-commands`. Use this
  only when the user wants workers on a different provider or self-hosted model.

## Step 4 — dispatch, as the controller

For `native-host`, launch every ready implementer **in parallel** with this
host's subagent-dispatch tool — named `Agent` in current Claude Code builds and
`Task` in older ones — using the `sia-implementer` agent and each operation's
`requested_model_id` where the host supports it.

The controller must not edit task-owned files itself. Brief, dispatch, review,
integrate, escalate — that separation is what makes the review independent.

Give each worker its brief path, its exact owned files, and the instruction to
write a non-empty report.

## Step 5 — ingest receipts truthfully

After each worker, write a receipt and ingest it:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" orchestrate receipt --file receipt.json
```

A receipt cites the plan ID and hash, the operation ID, agent identity,
requested and actual model, the report path, and usage.

**Never fabricate telemetry.** If Claude Code did not expose the actual model
or token usage, set `actual_model_id` to `null` and leave telemetry empty —
SIA then labels the figure `estimated` rather than `actual`. An invented number
silently corrupts every budget decision that follows.

## Step 6 — review, then integrate

Launch routed reviewers with the `sia-reviewer` agent only after implementers
complete. A reviewer must not be the agent that wrote the code.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" orchestrate status
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" integration --evidence <combined-validation>
```

Run integration only when `status` reports `complete`. Integration means the
whole combined diff was validated as one unit — not that each task passed its
own check in isolation.

## Budget stops

A hard ceiling stops scheduling before review. Capture it rather than raising
the ceiling reflexively:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/cli.py" capture --signal deviation \
  --error-class cost-overrun --context "<what overran and why>"
```
