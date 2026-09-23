---
name: sia
description: Run SIA's cost-aware multi-agent workflow only when the user explicitly invokes /sia.
disable-model-invocation: true
---

# SIA cost-aware orchestrator

<!-- managed-by-sia-adapter-v2 -->
Run `sia next --json` in the project root. Read `sia/AGENT.md` when vendored,
or run `sia guide` for the installed policy. Activation is explicit; other
skills and plugins remain available.

At execution, run `sia orchestrate plan --backend native-host --host claude`.
Use Claude Code's Agent tool to launch every ready implementer concurrently.
Pass each operation's exact `requested_model_id` when supported; custom agents
may define `model: haiku|sonnet|opus|<full-id>|inherit`. Use cheaper models for
bounded scans and current/strong models for demanding work and independent
review. Verify substitutions in `/tasks`.

For each worker, save a non-empty report and submit a JSON receipt containing
the immutable plan ID/hash, operation ID, agent/run identity, requested and
actual model, report path, and actual usage when exposed. Ingest it with
`sia orchestrate receipt --file <path>`. Launch routed reviewers after
implementers complete. Never claim telemetry or model identity Claude did not
expose, and never let the controller edit task-owned files.
