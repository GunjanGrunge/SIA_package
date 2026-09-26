# Changelog

All notable changes to the SIA package itself are recorded here.

## [0.6.0] - 2026-09-26

### Added

- **Every subagent gets the project's learned rules.** A `SubagentStart` hook
  injects active rules into each subagent at spawn, whoever spawns it (SIA's
  controller, Superpowers, or the user). Previously rules reached only the main
  session, so a subagent could repeat a mistake the user had already corrected.
- **SIA composes with installed skill frameworks.** `sia_doctor` now detects
  frameworks installed as plugins (Superpowers, BMAD) in Claude Code and Codex,
  not only ones vendored in the repository. When Superpowers is present:
  its skills author the spec and plan, SIA stays the single dispatcher, and
  `sia-implementer` / `sia-reviewer` subagents are told at spawn to use its
  practice skills (test-driven development, systematic debugging,
  verification). Both agents now have the `Skill` tool.
- **Tier routing reaches the spawn.** The orchestrate skill tells the
  controller to pass each operation's `requested_model_id` as the subagent's
  `model`, and offers `cheap: haiku, current: sonnet, strong: opus` as the
  Claude Code default. Without this the plan routed to cheap models but every
  subagent still ran on the expensive default.

### Fixed

- `sia_orchestrate_receipt` refuses a receipt file inside `.sia/`. In a live
  run the controller wrote its own receipts there, and integration rejected the
  whole run because it validates every file in that directory. The refusal
  names a safe location (`sdd/receipts/<operation>.json`).

### Verified

Two live end-to-end orchestrated runs in Claude Code: status `complete`,
integration recorded, tests passing, the implementer ran on Haiku and the
reviewer on Sonnet as routed, rules were present in every subagent transcript,
and the implementer invoked Superpowers' TDD and verification skills.

## [0.5.0] - 2026-09-26

### Added

- **SIA learns from corrections.** Any correction or lasting preference the
  user states becomes a standing rule for the project, with their exact words
  kept as evidence:
  - **Capture:** new `sia_rule_learn` MCP tool (and `sia rule learn`), which
    records the correction and creates the rule in one step. Rules could
    previously only be added from the CLI, so agents in Codex or Kiro could not
    create them at all. Also `sia_rule_list` and `sia_rule_retire`.
  - **Recall:** a `SessionStart` hook loads every active rule into each new
    session, and after `/compact`, so rules no longer depend on the agent
    remembering to run preflight.
  - **Enforcement:** rules may carry a `forbid` regex. A `PostToolUse` hook
    checks only the text the agent just wrote (never pre-existing content), and
    a `Stop` hook checks replies against rules that apply everywhere. Violations
    are pushed back to the agent. The Stop hook honours `stop_hook_active`, so
    an unsatisfiable rule cannot loop.
- **Kiro:** `mcp.json` (Kiro reads it; SIA shipped only `.mcp.json`), and the
  launcher searches Kiro's powers directory. Both MCP configs are generated
  from `tools/gen_mcp_config.py`, and a test fails if they drift.

### Fixed

- **Windows:** piped stdin was decoded with the legacy code page, so a project
  at `...\José_日本` was reported missing, and every protocol line ended in
  `\r\n`. Found by running under real Windows Python; both streams are now
  UTF-8 with `\n`.
- `sia_preflight` reported an unacknowledged medium or high rule as a tool
  error, so an agent could read "SIA broke" and skip the rules it returned.
- Guidance to make one rule per preference lives in the `sia_rule_learn` tool
  description itself: a live test showed agents call the tool without loading
  the skill, and merged three preferences into one rule.

### Security

- The MCP launcher never considers its working directory. Codex starts the
  server with the working directory set to the user's project, so trusting it
  would have executed any file named `sia_mcp.py` in an untrusted repository.

### Verified live in Claude Code

- A casual "never use em dashes, never say 'leverage', keep replies to three
  sentences" became three separate rules, each with the right check.
- A fresh session answered a CDN question in two sentences with no em dashes.
  The same question without the rules produced 2,488 characters and 15 em
  dashes.
- Asked to put banned text in a reply and in a file, the Stop and PostToolUse
  hooks each pushed back (confirmed in Claude Code's debug log) and the agent
  rewrote them.

### Known issues

- Recall and enforcement hooks ship for Codex, which supports hooks, but are
  untested there. Kiro uses its own hook system, so it gets capture (the MCP
  tool) but not automatic recall or enforcement yet.
- Kiro's agent path remains untested: the Kiro account hit its monthly usage
  limit before a session could run.

## [0.4.0] - 2026-09-24

### Added

- **SIA runs as an MCP server,** so every host can install it as a plugin with
  no `pip install`. `src/sia/mcp_server.py` speaks MCP over stdio using only the
  standard library — the official Python SDK is itself a pip dependency.
  Every tool delegates to the CLI, so behaviour and refusals are identical.
- **Manifests for Claude Code, Codex, Gemini CLI, Kiro and Antigravity:**
  `.mcp.json`, root `plugin.json` (Agent Plugins schema),
  `gemini-extension.json`, and `.agents/plugins/marketplace.json` for Codex.
- **Verified tool annotations.** Read-only labels were checked against a
  fingerprinted `.sia/`, and a test enforces them.

### Fixed — found by installing into Codex, none of it in Codex's docs

- **Codex silently drops a plugin at its marketplace root** (`"./"`, the layout
  Claude Code's marketplace uses) and lists zero plugins, with no error. The
  Codex marketplace now uses a `url` source.
- **Codex gives an MCP server no way to find its plugin.** Probed directly: no
  expansion of `${PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_ROOT}` or `$PLUGIN_ROOT` in
  arguments, no `PLUGIN_*` environment, and the working directory is the
  user's project. `.mcp.json` now runs a self-locating launcher: the root the
  host substituted, then the environment, then Codex's plugin cache, highest
  version first.
- **Tools with no annotations default to destructive and open-world** under the
  MCP spec, so Codex required approval even for a read-only status check, and
  per-server "approve" settings were ignored.
- `sia_doctor` reported "not initialized yet" as a tool failure, which made an
  agent stop at its first step. A diagnosis that runs is a result.
- Skill examples for `record`, `capture`, `rule add` and `preflight` were
  missing required flags or used flags that do not exist. All documented shapes
  now run in the test suite.

### Changed

- Skills call the MCP tools first, with the bundled CLI as a fallback.
  `allowed-tools` was removed: MCP tool names differ per host, so a restriction
  list cannot be portable and would block the very tools the skills need.
- `orchestrate run` is not exposed as a tool. Its `--approve-commands` flag is a
  human gate, and over MCP an agent could pass it to itself.

### Known issues

- Gemini CLI, Kiro and Antigravity are built to their documentation but
  untested; Gemini and Antigravity were not available to test against.
- Hosts launch `python3`. On Windows, where often only `python` or `py` exists,
  the plugin cannot start SIA.
- The review's High findings (see 0.3.1) are still not re-verified.

## [0.3.1] - 2026-09-24

### Added

- **Claude Code plugin.** `.claude-plugin/plugin.json` and `marketplace.json`,
  installable with `/plugin marketplace add GunjanGrunge/SIA_package` then
  `/plugin install sia@sia`.
- Skills `sia-start`, `sia-orchestrate` and `sia-workflow`; agents
  `sia-implementer` and `sia-reviewer`.
- **The CLI ships inside the plugin — no `pip install`.** `cli.py` is now the
  plugin entry point and puts `src/` on `sys.path` itself, so Python 3 is the
  only prerequisite.
- **Behavioural tests** in `tests/test_runtime_behaviour.py`. Until now `tests/`
  held only a string-pattern validator and three tests of that validator;
  nothing drove the runtime. The new suite runs the real CLI end to end and
  covers the budget ceiling, independent review, stage-gate refusals and
  placeholder rejection. Each budget test was mutation-checked against a
  deliberately reintroduced bypass.

### Fixed

- Execution-stage refusals name the current stage, the remaining stages and the
  exact next command. They previously stated the constraint alone, which made a
  working install read as a dead end: the quickstart completed without error
  and then every useful command refused.
- `orchestrate configure` rejects the `replace-with-*` placeholders emitted by
  `orchestrate example`. It previously accepted them and reported
  `"configured": true`, so the failure surfaced far from its cause.
- Framework detection widened beyond bmad/superpowers to `.claude`, `.agents`,
  `.kiro`, `.gemini` and `.antigravity`. On a real brownfield project it had
  detected one of five.
- `guides/orchestration.md` documents the cheap/current/strong tiers.
- **Non-Claude install instructions were broken.** PyPI only carries 0.2.0.
  Docs pinning `pip install sia-package==0.3.0` failed outright with "No
  matching distribution found", and docs saying plain `pip install sia-package`
  silently installed 0.2.0, which has no orchestration runtime at all. Codex,
  Kiro, Gemini CLI and Antigravity users now install from GitHub, which works
  today, until a release reaches PyPI.

### Changed

- README and the published user guide lead with the plugin install and explain
  the five evidence gates between `init` and `execution`.
- The `cli.py` contract check asserts the file documents `CLAUDE_PLUGIN_ROOT`
  and inserts `src/` on `sys.path`, instead of pinning a docstring describing
  it as a legacy shim.

### Removed

- Two stale `sia-vscode-extension-0.2.0.vsix` artifacts (repository root and
  `extension/`); `*.vsix` is now gitignored. The extension is built from source
  rather than shipped prebuilt.

### Known issues

- `docs/reviews/2026-09-18-sia-0.3-review.md` is a **NEEDS_CHANGES** review of
  an earlier state of this runtime.
  - Its **Critical hard-budget bypass is fixed** and now has regression tests.
    Verified by driving a run over its ceiling on the first receipt and on the
    final one: the overrun is terminal, later receipts are rejected, and
    integration is blocked. A previous version of this changelog listed it as
    open without having tested it; that was wrong.
  - Its **High findings have not been re-verified** against this code. Treat
    them as open until each is checked: mutable hashed briefs, stale integration
    receipts, ownership-transfer bypass, unbounded or cancellation-unsafe
    subprocesses, inline prompt disclosure, silent strong-to-current routing.
- 0.3.x is not yet on PyPI; see the install fix above.
- No orchestration run has yet dispatched a live worker. Verification so far
  stops at plan creation and recorded receipts.

## [0.3.0] - 2026-09-18

### Added

- Real multi-agent orchestration with shared native-host and standalone
  backends.
- Deterministic cheap/current/strong model routing by task role, risk, and
  complexity.
- Immutable dispatch plans, concurrent implementers, independent routed
  reviewers, receipts, timeout/output controls, and shell-free command arrays.
- Atomic token/USD reservations, warning/hard budget gates, configured pricing,
  and actual/calculated/estimated/unknown telemetry quality.
- First-class Gemini CLI adapter and v2 managed protocols for Claude Code,
  Codex, Kiro, and Antigravity.
- Receipt-bound integration evidence manifests and safe adapter upgrades.

### Changed

- Multi-agent cost optimization is now SIA's primary orchestration workflow;
  evidence-only task commands remain backward compatible.
- Native host plans request exact configured model IDs without guessing the
  active IDE model; unknown model/run/usage data remains explicitly unknown.

## [0.2.0] - 2026-09-18

### Added

- Installable `sia`/`sia-agent` Python CLI and packaged workflow policy.
- Durable `.sia/` state for stages, task evidence, feedback events, rules,
  preflight checks, and convergence metrics.
- Explicit `advisory`, `planning`, and `orchestrator` runtime modes.
- Opt-in adapters for Claude Code, Codex, Kiro, and Antigravity.
- Configurable stage ownership for BMAD, Superpowers, and other frameworks.
- Evidence-limited modular project-skill synthesis and
  `sdd/skill-manifest.md` guidance.
- Existing-project repository-informed, goal-first, and conversational intake
  approaches.
- Public attribution policy that preserves the human Git author.
- Complete usage and extension-publishing documentation.
- Optional VS Code-compatible control-center extension.

### Changed

- SIA resumes from `sia next --json` instead of relying on conversational
  context to retain the active stage.
- Active state mutations serialize across host-agent processes.
- Parallel tasks require canonical, non-overlapping file ownership, including
  parent/child and Windows case-insensitive path protection.
- Controllers may not silently substitute direct implementation for a
  dispatched subagent task.
- Feedback uses reusable error classes and provenance-bearing active/retired
  rules.
- Host adapters are manual and namespaced so other plugins remain available.
- Heavy root assets were removed; extension branding lives under `extension/`.
- Token/cost savings are estimates unless backed by host telemetry.

### Security

- Adapter installation rejects collisions and redirected paths outside the
  project root; removal requires exact managed content.
- Integration requires independent reviews and is invalidated when execution
  evidence changes.
- Extension initialization/status delegates to the canonical persistent CLI
  instead of overwriting host instruction files.

## [0.1.0] - 2026-09-13

### Added

- Markdown bootstrap and authority order in `AGENT.md`.
- Intake, approval, specification, planning, subagent, and security guides,
  including `guides/security-gate.md`.
- Feedback capture in `capture-interface.md`, PASS/DEVIATION classification,
  convergence signals, rule provenance, and rule expiry guidance.
- Terminal launch banner and plain-text fallback.
- Claude Code discovery shim.
- Structural package validator and manual dogfood scenarios.
