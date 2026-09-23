---
name: sia
description: Run SIA's cost-aware multi-agent workflow only when the user explicitly requests SIA.
---

# SIA cost-aware orchestrator

<!-- managed-by-sia-adapter-v2 -->
Run `sia next --json`, then at SIA-owned execution run
`sia orchestrate plan --backend native-host --host codex`.

Ask Codex to spawn one agent per ready operation in parallel and wait for all.
Use each operation's requested model and reasoning effort through the spawn
request or custom agent configuration. Keep the repository's `AGENTS.md`, MCP,
and existing `.agents/skills` active. Prefer efficient models for bounded
exploration/tests and current/strong models for complex implementation and
independent review.

Save every report and ingest a receipt with `sia orchestrate receipt --file`.
The receipt must name the plan ID/hash, operation, actual agent/thread/model
when exposed, and actual usage when available. Never invent missing telemetry.
The controller coordinates and integrates; it does not edit dispatched files.
