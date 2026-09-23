# Changelog

All notable changes to the SIA package itself are recorded here.

## [Unreleased]

### Added

- **Claude Code plugin.** `.claude-plugin/plugin.json` and `marketplace.json`,
  installable with `/plugin marketplace add GunjanGrunge/SIA_package` then
  `/plugin install sia@sia`.
- Skills `sia-start`, `sia-orchestrate` and `sia-workflow`; agents
  `sia-implementer` and `sia-reviewer`.
- **The CLI ships inside the plugin — no `pip install`.** `cli.py` is now the
  plugin entry point and puts `src/` on `sys.path` itself, so Python 3 is the
  only prerequisite. The PyPI package remains the path for other hosts.

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

- `docs/reviews/2026-09-18-sia-0.3-review.md` records a **NEEDS_CHANGES** review
  of this runtime with a confirmed Critical hard-budget bypass and several High
  findings. None are addressed here.

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
