# Cost-Aware Multi-Agent Orchestration

## Purpose

SIA manages multiple workers without assuming every coding assistant exposes
the same API. One immutable dispatch plan supports native-host spawning and
standalone command workers. SIA preserves plugin boundaries, exact file
ownership, independent review, budgets, and truthful telemetry.

Every operation routes to one of three explicitly configured model tiers —
cheap/current/strong — selected by task role, risk, and complexity. SIA never
infers a tier from a model name and never guesses the host's selected model.

## Configure Models, Budget, And Concurrency

Generate a starter JSON object with `sia orchestrate example`, save it, replace
every model ID with an exact provider/host identifier, then run:

```text
sia orchestrate configure --file orchestration.json
```

Minimum native-host configuration:

```json
{
  "models": {
    "cheap": {"id": "provider-cheap-model", "input_usd_per_million": 0, "output_usd_per_million": 0},
    "current": {"id": "selected-current-model", "input_usd_per_million": 0, "output_usd_per_million": 0},
    "strong": {"id": "provider-strong-model", "input_usd_per_million": 0, "output_usd_per_million": 0}
  },
  "budget": {"max_tokens": 500000, "max_cost_usd": 25, "warning_fraction": 0.8},
  "concurrency": {"global": 4, "cheap": 4, "current": 2, "strong": 1},
  "routing": {
    "low": "cheap", "normal": "current", "high": "strong",
    "review": "current", "escalation": ["cheap", "current", "strong"]
  },
  "allow_model_fallback": false,
  "timeout_seconds": 900,
  "workers": {}
}
```

Zero prices are allowed but produce no cost estimate. SIA never downloads a
model, guesses an IDE selection, or stores API tokens in config.

## Prepare Tasks

```text
sia task prepare --task docs --brief sdd/docs.md --files docs/guide.md \
  --risk low --complexity simple --estimated-tokens 8000
sia task prepare --task auth --brief sdd/auth.md --files src/auth.py \
  --risk high --complexity complex --estimated-tokens 40000
```

Low/simple implementation routes to cheap. Normal routes to current.
High/complex routes to strong. Reviews route to current, except high-risk review
routes to strong. All decisions and reasons are persisted.

## Native Host Backend

```text
sia orchestrate plan --backend native-host --host kiro
sia orchestrate status
```

The active host consumes every ready operation and spawns native subagents.
After a worker completes, ingest a receipt:

```json
{
  "schema_version": 1,
  "plan_id": "plan-...",
  "plan_hash": "...",
  "operation_id": "auth:implement",
  "status": "complete",
  "provenance": "native_attested",
  "host": "kiro",
  "agent_id": "sia-auth-implementer",
  "native_run_id": "host-run-or-unknown-id",
  "requested_model_id": "provider-strong-model",
  "actual_model_id": null,
  "report_path": "sdd/auth-report.md",
  "telemetry": {}
}
```

Run `sia orchestrate receipt --file receipt.json`. `actual_model_id: null` and
empty telemetry are valid when a host does not expose them; SIA applies the
persisted estimate. Never fabricate values.

## Standalone Backend

Standalone config additionally defines a command-array worker per tier or one
`default`. Placeholders must be entire arguments:

```json
{
  "workers": {
    "cheap": {
      "argv": ["provider-cli", "run", "--model", "{model_id}", "--prompt-file", "{prompt_path}"],
      "env_allow": ["PROVIDER_API_KEY"],
      "timeout_seconds": 600
    }
  }
}
```

The provider command is illustrative; use syntax from the installed CLI. SIA
stores environment variable names but never their values. Then run:

```text
sia orchestrate plan --backend standalone --host provider-cli
sia orchestrate run --approve-commands
```

SIA launches ready implementers concurrently with `shell=False`, waits,
validates receipts, and then launches independent reviewers. Standard output is
the report. A worker may append one telemetry line:

```text
SIA_USAGE_JSON: {"model_id":"exact-model","input_tokens":1200,"output_tokens":300}
```

Without this line, usage remains estimated. A provider-reported cost is actual;
actual tokens multiplied by configured rates are calculated, not billed actual.

## Budget And Stop Rules

Plan creation reserves all estimated operation tokens/cost under the project
lock. It rejects a plan above either hard ceiling and warns at the configured
fraction. Receipts reconcile usage. Standalone scheduling stops before review
when implementation receipts exceed a hard ceiling. Timeouts, non-zero exits,
empty reports, model mismatch (unless fallback is allowed), invalid paths, or
receipt/hash mismatch fail the operation. Capture a hard ceiling as a DEVIATION
with `error_class: cost-overrun`.

## Plugin Coexistence

Only orchestrator mode, execution stage, and owner `sia` may launch. When BMAD,
Superpowers, or another plugin owns execution, SIA emits a handoff and starts
nothing. Native plugins may be used by workers as capabilities but may not
replace `.sia/` state or alter another task's owned files.

## Evidence Layout

```text
.sia/runs/<run-id>/
├── dispatch-plan.json
├── integration.md
└── tasks/<task-id>/
    ├── brief.md
    ├── task.json
    ├── orchestrated-report.md
    ├── orchestrated-review.md
    ├── receipts/
    └── attempts/<attempt-id>/
        ├── prompt.md
        ├── request.json
        ├── stdout.log
        ├── stderr.log
        └── receipt.json
```

Standalone execution is process isolation, not a security sandbox. Workers run
with the current user's filesystem/network permissions. Use narrow tools,
separate worktrees/containers where supported, and review evidence for secrets
before committing it.
