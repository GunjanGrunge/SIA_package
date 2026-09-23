# Host Integration Contract

SIA has one durable control plane: the `sia` CLI and project-local `.sia/`
state. A host adapter is an explicit launcher for SIA's immutable dispatch plan,
not a second workflow engine.

## Execution Backends

| Backend | Who starts workers | What SIA observes |
|---|---|---|
| `native-host` | The active Claude, Codex, Kiro, Gemini, or Antigravity controller uses native subagent tools | Caller-attested agent/thread/model/usage receipts |
| `standalone` | SIA runs user-approved command arrays with `shell=False` | Process, timeout, output, model request, and receipt evidence |

Both backends share one model router, token/USD budget, concurrency policy,
operation DAG, receipt schema, task ownership contract, and integration gate.
Standalone processes are observed but are not an OS filesystem/network sandbox.

## Runtime Modes And Plugin Ownership

| Mode | SIA owns | Worker behavior |
|---|---|---|
| `advisory` | feedback, rules, preflight, convergence | never starts workers |
| `planning` | intake through plan | never starts workers |
| `orchestrator` | full evidence pipeline | may launch only at execution when owner is `sia` |

The `bridge` framework policy remains default. BMAD, Superpowers, MCP, native
skills, and custom plugins remain available. Assign stages with
`sia owner --stage <stage> --to <owner>`. If another framework owns execution,
SIA emits a handoff and launches nothing.

## Cost-Aware Model Routing

The user explicitly configures exact provider IDs for three logical tiers:

- **cheap** — bounded exploration, routine tests, documentation, simple/low-risk tasks;
- **current** — the user's selected/default capable model for normal work and review;
- **strong** — high-risk, security, architecture, complex escalation, or high-risk review.

SIA never guesses the currently selected IDE model. A dispatch plan records the
requested tier/model and routing reason. Receipts record the actual model or
`unknown`. Configured-price calculations are `calculated`; heuristic usage is
`estimated`; provider/worker-reported usage may be `actual`.

## Native Re-entry And Receipt Protocol

1. Run `sia next --json`.
2. Prepare tasks with exact files, risk, complexity, and optional token estimate.
3. Run `sia orchestrate plan --backend native-host --host <host>`.
4. Spawn all ready implementers in parallel using each requested model.
5. Save each report and create a receipt with plan ID/hash, operation ID,
   agent/run identity, requested/actual model, report path, and telemetry.
6. Run `sia orchestrate receipt --file <receipt.json>`.
7. Launch newly-ready independent reviewers and ingest their receipts.
8. Run integration only when `sia orchestrate status` reports `complete`.

Native IDs and telemetry remain attestations unless a host exposes verifiable
metadata. Unknown data must stay unknown.

## Adapter Locations And Capabilities

| Host | Adapter | Native model control |
|---|---|---|
| Claude Code | `.claude/skills/sia/SKILL.md` | per invocation or `.claude/agents/*.md` model |
| Codex | `.agents/skills/sia/SKILL.md` | custom agent model/reasoning effort |
| Kiro | `.kiro/steering/sia.md` | `.kiro/agents/*` top-level model |
| Gemini CLI | `.gemini/skills/sia/SKILL.md` | `.gemini/agents/*.md` model |
| Antigravity | `.agents/workflows/sia.md` | coordinator/UI/profile when exposed |

Install with `sia adapter install --host claude|codex|kiro|gemini|antigravity`.
Use `--upgrade` only to replace an unchanged SIA-managed v1 adapter. SIA refuses
collisions, modified files, and redirected paths outside the project.

## Standalone Worker Security

Standalone workers are configured as argument arrays, never command strings.
Placeholders must occupy a whole argument. SIA uses
`asyncio.create_subprocess_exec(..., shell=False)`, project-root `cwd`, no
inherited stdin, a minimal environment plus named allowlist, timeout/kill,
bounded logs, and an explicit `--approve-commands` gate. Configuration must not
contain secret values; refer only to environment variable names. Worker output
is untrusted and must pass receipt/path/model/budget validation.
