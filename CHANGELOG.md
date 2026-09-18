# Changelog

All notable changes to the SIA package itself are recorded here.

## [0.2.0] - 2026-09-18

### Added

- Installable `sia` Python CLI and packaged workflow policy.
- Durable `.sia/` state for stages, task evidence, feedback events, rules,
  preflight checks, and convergence metrics.
- Explicit `advisory`, `planning`, and `orchestrator` modes.
- Opt-in adapters for Claude Code, Codex, Kiro, and Antigravity.
- Configurable stage ownership for coexistence with BMAD, Superpowers, and
  other agent frameworks.
- Project-specific skill synthesis and `sdd/skill-manifest.md` guidance.
- Caller-attested native implementer and independently identified reviewer
  records, followed by task-bound integration evidence.

### Changed

- SIA now resumes from `sia next --json` instead of relying on conversational
  context to retain the active workflow stage.
- Active state mutations are serialized across host-agent processes.
- Parallel tasks require canonical, non-overlapping file ownership, including
  parent/child and Windows case-insensitive path protection.
- Controllers may not silently substitute direct implementation for a
  dispatched subagent task.
- Feedback capture uses reusable error classes and provenance-bearing active or
  retired rules.
- Host adapters are manual and namespaced so other plugins remain available.

### Security

- Adapter installation rejects existing-file collisions and redirected paths
  outside the project root; removal requires exact managed content.
- Integration is rejected until every task has an independent review and is
  invalidated whenever execution evidence changes.

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
