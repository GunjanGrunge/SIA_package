---
inclusion: manual
---

# SIA cost-aware orchestrator

<!-- managed-by-sia-adapter-v2 -->
Run `sia next --json`, then at SIA-owned execution run
`sia orchestrate plan --backend native-host --host kiro`.

Use Kiro's native subagent tool and project profiles in `.kiro/agents/`.
Map cheap/current/strong operations to profiles whose top-level `model` uses
the exact configured model ID. Independent dependency-graph nodes may run in
parallel. Kiro has no documented external per-delegation model parameter, so
use profiles rather than guessing the active IDE model. If a child model,
run ID, or token/cost data is unavailable, record it as unknown.

Save reports and ingest one receipt per operation with
`sia orchestrate receipt --file`. Keep BMAD, Superpowers, steering, skills,
hooks, and MCP active. SIA owns `.sia/` state and must not overwrite them.
