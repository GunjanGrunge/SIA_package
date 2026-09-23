---
description: Run SIA's cost-aware parallel multi-agent workflow
---

# SIA cost-aware orchestrator

<!-- managed-by-sia-adapter-v2 -->
On `/sia`, run `sia next --json`, then at SIA-owned execution run
`sia orchestrate plan --backend native-host --host antigravity`.

Use Antigravity's coordinator to launch every independent ready operation in
parallel. Request the exact routed model tier where the UI or agent profile
supports it, collect each artifact/report, and ingest one receipt per operation
with `sia orchestrate receipt --file`. Use current/strong routed agents for
independent review after implementations complete. Record unknown rather than
inventing model, run, token, or cost telemetry. Do not alter other `.agents/`
workflows, skills, agents, or plugin files.
