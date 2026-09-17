# Changelog

All notable changes to the SIA package itself (not to any project that
uses it) are recorded here.

## [0.2.0] - 2026-09-17

### Fixed & Enhanced

- **Asset Directory Clean-up**: Removed heavy `assets/` directory (including 1.8MB flowchart) from release package for clean, lightweight user distribution. README updated with portable ASCII/markdown pipeline architecture.
- **Working Directory Execution Safety**: Enforced project root execution across `AGENT.md`, `guides/subagent-task-brief.md`, and `USAGE.md`. Project files (`main.py`, `main.js`, tests, subagents) MUST execute in the user project root, never inside `.claude/workingtree/` or temporary sandboxes.
- **Host Engine & Harness Visibility**: Added automatic host engine detection (`Claude Code`, `Antigravity IDE`, `Codex CLI`, etc.) and status headers to launch screens, task dispatches, and reports.
- **Token Savings Accounting**: Added `Tokens Used`, `Baseline Context Cost`, `Tokens Saved`, and `% Reduction` tracking and reporting across Intake, Task Reports, Progress Log (`sdd/progress.md`), Integration Report, and CLI status check.
- **Modular Feature Skill Decomposition**: Upgraded `guides/writing-project-skills.md` from single-skill generation to synthesizing **Modular Feature Skill Packs** (`skills/<project>-<feature>/SKILL.md`), enabling cross-engine collaboration across Claude, Codex, Antigravity, Cursor, etc.
- **Status Check CLI & Mid-Project Invocation**: Added `python sia/banner.py --status` CLI tool to audit active SIA phase, modular skills, token savings, and working directory safety. Added explicit brownfield mid-project invocation guide to `USAGE.md`.

## [Unreleased]

### Added

- `USAGE.md` — complete new-project, existing-project, Claude Code, and
  Codex instructions for users of the package.
- Project-skill synthesis guide and manifest: SIA now generates a
  project-specific operating skill from approved project evidence instead
  of asking users to author skills themselves.
- Execution evidence gate: implementation tasks require durable brief,
  host-dispatch, subagent-report, reviewer, progress, and integration
  evidence.
- Existing-project Intake modes: users can choose bounded repository
  exploration, goal-first work without a broad scan, or conversational
  discovery; SIA records evidence, knowns, unknowns, and the goal.
- Public-distribution attribution default: SIA adds a README badge and
  SIA-mediated commit trailers without a user toggle, while preserving the
  human Git identity and pointing to durable evidence. A direct user override
  can disable future attribution for that project.

### Changed

- Controllers may no longer silently substitute direct implementation for
  a planned subagent task when the host supports subagent dispatch.

## [0.1.0] - 2026-09-13

Initial package, implementing the design specified in
`docs/superpowers/specs/2026-09-13-sia-design.md` (a design doc from
SIA's own development history — not a file shipped in this package):

- `AGENT.md` — bootstrap and pipeline.
- `guides/security-gate.md` — fixed threat-class checklist.
- `guides/questioning-and-approval.md` — batching and severity gates.
- `guides/writing-agent-md.md` — project AGENT.md authoring guide.
- `guides/writing-spec.md` — project spec authoring guide.
- `guides/writing-plan.md` — project plan authoring guide.
- `guides/subagent-task-brief.md` — task brief/report/progress formats.
- `capture-interface.md` — feedback schema and self-healing loop
  engineering (PASS/DEVIATION, pre-flight self-check, convergence
  signal, rule hygiene).
- `VALIDATION.md` — manual dogfood validation checklist (5 scenarios).
- `tests/validate_sia.py` — the structure-test harness (dev tooling for
  building the package, not something copied into a target project).

## [Unreleased]

- `banner.py` — terminal launch-screen banner (Hexagonal Prism mark, Electric
  Cyan), run at Bootstrap when the host can execute shell commands.
- `BANNER.txt` — pre-rendered plain-text fallback of the same banner, for
  hosts that cannot execute shell commands.
- `AGENT.md` — added a "Launch Screen" section wiring both into the
  Bootstrap pipeline step; added a pointer to `INSTALL.md` for first-time
  setup.
- `INSTALL.md` — how to add SIA to a project: gitignoring the vendored
  `sia/` folder while keeping generated artifacts (that project's own
  `AGENT.md`, specs, plans, session logs) committed — mirroring how BMAD's
  `.claude/`/`_bmad/` are gitignored but `_bmad-output/` is kept.
- `integrations/claude-code/SKILL.md` — optional, thin Claude Code
  discovery shim; defers entirely to `AGENT.md` as the source of truth.
- `AGENT.md` — added an Authority Order section (user instructions >
  project AGENT.md > approved spec/plan > SIA guides > subagent brief)
  and an Integration phase at the end of pipeline step 6 (Execution).
- `guides/writing-plan.md` — added Owned Files: each task's Files block
  is now an exclusive ownership boundary; overlapping file changes
  require a dedicated integration task rather than silent overlap.
- `guides/subagent-task-brief.md` — added an Effort Budget field and a
  fixed escalation list to the Task Brief Format (stop and report rather
  than improvise past an unexpected dependency, conflicting file,
  ambiguous requirement, missing tool, or unrelated failing test); added
  an Integration Report Format.
- `guides/writing-spec.md` — resolved a tension between this guide's
  "confirm section by section" and `questioning-and-approval.md`'s
  batching rule: one approved pattern now applies (batch every question,
  draft the complete spec, one structured approval round — except a
  High-severity decision surfaced mid-draft, confirmed before
  continuing).
- `capture-interface.md` — `capture()` gained a fourth field,
  `error_class` (a reusable label for the *kind* of mistake, e.g.
  `unsafe-edit-target`, `missing-approval`, `interface-assumption`,
  `unverified-claim`); added a Rule Provenance section (source event,
  evidence, severity, error class, scope, date, active/retired status —
  every rule carries these, not just its sentence); Convergence Signal
  now tracks deviation rate per error class, not only overall; added
  Rule Review And Expiry (a periodic check that retires stale/superseded
  rules rather than leaving them to silently accumulate).
- `guides/writing-agent-md.md` — Accumulated Feedback Rules now require
  the full provenance record per rule.
- `guides/subagent-task-brief.md` — Task Brief Format gained a Relevant
  Standing Rules field (rules travel *with* a subagent's brief, since a
  scoped subagent has no reason to read the whole project AGENT.md);
  reviewers (task-level and Integration) must now state which standing
  rules were checked and their per-rule verdict, not just whether the
  code works.
- `capture-interface.md` — added a Token / Cost Tracking section: a
  running usage total across a session/plan run, checked against a
  project-stated ceiling, with an explicit approval-gated response
  (scope reduction or cheaper model) on hitting it, logged via
  `capture()` with `error_class: cost-overrun`.
- `guides/writing-agent-md.md` — added an optional Competing Agent
  Framework Boundary required section, for projects where Intake found
  pre-existing agent/AI-tooling already installed: coexist, never edit
  it, document the boundary.
- `AGENT.md` — Intake step now also flags any pre-existing agent/AI
  tooling for the Competing Agent Framework Boundary section, and adds
  a soft exploration budget (15 files / ~40k tokens by default) during
  Intake, with an explicit ask-rather-than-continue path if more is
  genuinely needed.
