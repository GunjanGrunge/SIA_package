# SIA (Self-Improving Agents)

<p align="center">
  <img src="https://img.shields.io/badge/version-0.4.0-00F2FE.svg?style=flat-square" alt="Version 0.4.0" />
  <img src="https://img.shields.io/badge/status-active-success.svg?style=flat-square" alt="Status: Active" />
  <img src="https://img.shields.io/badge/license-MIT-lightgrey.svg?style=flat-square" alt="License: MIT" />
  <img src="https://img.shields.io/badge/host--agnostic-yes-7B2CBF.svg?style=flat-square" alt="Host-agnostic" />
</p>

<p align="center">
  <a href="https://gunjangrunge.github.io/SIA_package/"><strong>📘 Open the Complete SIA User Guide</strong></a>
  · Claude Code · Codex · Gemini CLI · Antigravity · Kiro
</p>

<p align="center"><b>Persistent, host-neutral orchestration for self-improving coding agents.</b></p>

SIA is a persistent, host-neutral multi-agent control plane. It decomposes
approved work into ownership-safe operations, routes bounded tasks to explicitly
configured cheaper models, preserves the selected/current model for normal
coordination, escalates complex/high-risk work to a strong tier, launches
independent workers in parallel, and requires separate review before
integration. State, receipts, budgets, and telemetry survive new chats under
`.sia/`.

Use **native-host orchestration** when Claude Code, Codex, Kiro, Gemini CLI, or
Antigravity should spawn its own subagents. Use **standalone orchestration** when
SIA should launch user-approved provider CLI command arrays itself. BMAD,
Superpowers, MCP, and other plugins remain available through bridge ownership.

## Install

SIA installs as a plugin in each host. **There is no `pip install`**: the plugin
bundles SIA and runs it as an MCP server that the host starts for you. Python 3
is the only prerequisite.

| Host | Install | Status |
|---|---|---|
| **Claude Code** | `/plugin marketplace add GunjanGrunge/SIA_package`<br>`/plugin install sia@sia` | ✅ Verified end to end |
| **Codex** | `codex plugin marketplace add GunjanGrunge/SIA_package`<br>`codex plugin add sia@sia` | ✅ Verified end to end (see note) |
| **Gemini CLI** | `gemini extensions install https://github.com/GunjanGrunge/SIA_package` | ⚠️ Built to Gemini's docs; not yet tested |
| **Kiro** | Install a power from the GitHub URL | ⚠️ Not yet tested |
| **Antigravity** | `agy plugin install <path-to-a-clone>` | ⚠️ Not yet tested |

`sia@sia` is `plugin@marketplace`. Then say **"set up SIA on this project"**.
The `sia-start` skill walks the project from intake to execution.

**Codex asks before SIA writes.** Read-only tools (status, next, doctor,
preflight, …) run without a prompt; tools that change `.sia/` ask for approval,
which is Codex protecting you. In a non-interactive `codex exec` run there is
nobody to answer, so the call is cancelled. To allow SIA's own tools there —
and only SIA's — add:

```text
-c 'plugins."sia@sia".mcp_servers.sia.default_tools_approval_mode="approve"'
```

**Windows hosts** launch the command `python3`. If only `python` or `py` is on
your `PATH`, the plugin cannot start SIA. Check with `python3 --version` before
installing; the Microsoft Store build of Python provides `python3`.

The plugin ships three skills (`sia-start`, `sia-orchestrate`, `sia-workflow`)
and two agents (`sia-implementer`, `sia-reviewer`).

**What it can do on your machine:** by default SIA only reads and writes
`.sia/` and asks *this host* to spawn its own subagents. The optional
`standalone` backend additionally launches provider CLIs you configure, as
argument arrays with `shell=False`, behind an explicit
`orchestrate run --approve-commands` gate. That is the plugin's largest
capability surface; it is opt-in and never runs a shell string.

### The CLI on its own, without a host plugin

Only needed for scripting SIA outside an agent host, or for the `standalone`
backend's `orchestrate run --approve-commands`, which is deliberately not
exposed to agents.

```powershell
python -m pip install "git+https://github.com/GunjanGrunge/SIA_package"
sia init --mode orchestrator
```

This installs from GitHub on purpose: PyPI's `sia-package` is still 0.2.0, which
has no orchestration runtime. You can also vendor this repository as `sia/`; see
[`INSTALL.md`](./INSTALL.md). No provider API key or cloud service is required
by SIA itself.

### What happens after init — read this before reporting a bug

`init` leaves the project at the **`intake`** stage. In orchestrator mode,
`task prepare` and `orchestrate plan` are illegal until the project reaches
**`execution`**, which is five evidence-gated advances away:

```text
intake -> spec -> project-instructions -> skills -> plan -> execution
```

```text
sia next --json                  # what this stage requires
sia advance --evidence <path>    # once that artifact exists
```

This is deliberate: a stage transition needs an artifact on disk, never a claim
in conversation. Configuring orchestration before reaching `execution` succeeds
and then refuses to dispatch — the refusal names the stage and the next
command. Use `advisory` mode if you want SIA's feedback loop without the gates.

## Core commands

```text
sia init --mode advisory|planning|orchestrator
sia next --json                  durable host re-entry packet
sia advance --evidence <path>    evidence-gated stage transition
sia task prepare ...             define owned files, risk, complexity, estimate
sia orchestrate configure ...    store models, prices, budgets, concurrency
sia orchestrate plan ...         route operations and reserve budget
sia orchestrate run ...          launch approved standalone workers in parallel
sia orchestrate receipt ...      ingest native-host worker evidence
sia orchestrate status           show operations, budget, telemetry quality
sia integration --evidence ...   bind all receipts and combined validation
sia record ... / sia capture ... persist PASS/DEVIATION outcomes
sia rule add ... / sia preflight ... / sia convergence
sia adapter install --host ...   install an explicit, namespaced launcher
sia owner --stage plan --to bmad assign stage ownership in bridge mode
sia doctor                       diagnose project integration
```

SIA can launch real standalone subprocess workers and can make the active host
launch native subagents from the same immutable plan. Native-host identities
and telemetry remain caller-attested because vendors expose different APIs;
standalone process execution is observed but is not an OS security sandbox.
Actual, calculated, estimated, and unknown telemetry are labeled separately.
See
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
