---
name: sia
description: Run SIA's cost-aware multi-agent workflow only when explicitly requested.
---

# SIA cost-aware orchestrator

<!-- managed-by-sia-adapter-v2 -->
Run `sia next --json`, then at SIA-owned execution run
`sia orchestrate plan --backend native-host --host gemini`.

Use Gemini CLI native subagents from `.gemini/agents/*.md` or built-ins.
Custom agent frontmatter supports exact `model`, tools, `max_turns`, and
`timeout_mins`. Launch independent ready operations concurrently where the host
supports it; Gemini subagents cannot recursively spawn more subagents. Keep
`GEMINI.md`, existing skills, settings, hooks, MCP, and policy rules active.

Save each report and ingest a receipt with `sia orchestrate receipt --file`.
Use the routed current/strong model for independent reviewers. Record telemetry
as unknown/estimated unless Gemini exposes actual values; never infer them.
