# SIA (Self-Improving Agents)

<p align="center">
  <img src="https://img.shields.io/badge/version-0.2.0-00F2FE.svg?style=flat-square" alt="Version 0.2.0" />
  <img src="https://img.shields.io/badge/status-active-success.svg?style=flat-square" alt="Status: Active" />
  <img src="https://img.shields.io/badge/license-MIT-lightgrey.svg?style=flat-square" alt="License: MIT" />
  <img src="https://img.shields.io/badge/host--agnostic-yes-7B2CBF.svg?style=flat-square" alt="Host-agnostic" />
</p>

<p align="center">
  <a href="https://gunjangrunge.github.io/SIA_package/"><strong>📘 Open the Complete SIA User Guide</strong></a>
  · Claude Code · Codex · Gemini CLI · Antigravity · Kiro
</p>

<p align="center"><b>Persistent, host-neutral orchestration for self-improving coding agents.</b></p>

SIA combines detailed workflow guidance with an installable Python CLI. The CLI
keeps the current stage, subagent evidence, feedback events, standing rules,
and convergence data under `.sia/`, so SIA survives fresh chats and context
compaction instead of appearing only at the beginning of a session.

SIA supports three explicit modes: `advisory`, `planning`, and `orchestrator`.
Its host adapters are manual launchers, so BMAD, Superpowers, and other plugins
remain usable in parallel.

## Install

```powershell
python -m pip install sia-package
sia init --mode orchestrator
sia adapter install --host kiro
sia next --json
```

Replace `kiro` with `claude`, `codex`, or `antigravity`. You can also vendor
this repository as `sia/`; see [`INSTALL.md`](./INSTALL.md). No provider API
key or cloud service is required by SIA itself.

## Core commands

```text
sia init --mode advisory|planning|orchestrator
sia next --json                  durable host re-entry packet
sia advance --evidence <path>    evidence-gated stage transition
sia task prepare ...             establish exclusive file ownership
sia task dispatch ...            persist native host agent/run identity
sia task finish ...              attach report + independently identified review
sia integration --evidence ...   attach combined validation/review
sia record ... / sia capture ... persist PASS/DEVIATION outcomes
sia rule add ... / sia preflight ... / sia convergence
sia adapter install --host ...   install an explicit, namespaced launcher
sia owner --stage plan --to bmad assign stage ownership in bridge mode
sia doctor                       diagnose project integration
```

The CLI does not fake universal agent spawning. Claude Code, Codex, Kiro, and
Antigravity create agents through their own native harnesses; SIA checks the
ordering, ownership, and completeness of the common brief/dispatch/review
record. Native IDs are caller-attested because vendor harnesses do not expose
one shared authentication API. See
[`HOST-INTEGRATION.md`](./HOST-INTEGRATION.md).

## Architecture

```text
host /sia command
       │
       ▼
sia next --json ──► .sia/config.json + .sia/state.json
       │
       ├── guidance: AGENT.md / installed `sia guide`
       ├── native agents: host-owned spawning and parallelism
       ├── evidence: .sia/runs/<run-id>/
       └── learning: events.jsonl + rules.json + preflight/convergence
```

## Repository layout

```text
src/sia/                         # installable CLI and orchestration runtime
AGENT.md                         # detailed vendored workflow policy
HOST-INTEGRATION.md              # modes, adapters, and coexistence contract
guides/                          # spec/plan/skill/task/security guidance
integrations/                    # source shims for supported hosts
capture-interface.md             # feedback and convergence semantics
tests/validate_sia.py            # package contract validator
```

## Coexistence

The default `bridge` policy detects common framework folders, records them in
`.sia/config.json`, never replaces root `AGENT.md`/`AGENTS.md`, and refuses to
overwrite adapter files. Choose `advisory` when another framework owns the
whole development workflow, `planning` when it owns execution, or
`orchestrator` when SIA should own native-agent dispatch and integration.

## Existing Projects And Attribution

For existing repositories, choose a repository-informed, goal-first, or
conversational intake approach independently of SIA's persisted runtime mode.
SIA records evidence, knowns, unknowns, and competing framework boundaries
without claiming to understand unread files. Public SIA-mediated work follows
[`guides/attribution.md`](./guides/attribution.md): the human remains the Git
author while README and `Assisted-by: SIA` / `SIA-Run:` evidence identify the
workflow. See [`USAGE.md`](./USAGE.md) for complete host and brownfield usage.

## VS Code And Compatible IDEs

The optional extension under `extension/` exposes initialization and status UI
for VS Code-compatible IDEs. The Python CLI and `.sia/` state remain the
canonical backend; extension UI must not be treated as independent workflow
state or verified token telemetry.

## Validation

Run `python tests/validate_sia.py`, `python -m compileall src`, and a CLI smoke
run in a temporary project. `VALIDATION.md` contains host-level dogfood
scenarios that cannot be proven by structural tests alone.

## License

MIT.
