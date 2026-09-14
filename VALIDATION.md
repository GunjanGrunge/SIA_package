# Validation: Dogfooding SIA Before Calling A Version Stable

SIA is instructions, not executable application code — `tests/validate_sia.py`
only proves no required section is missing, never that the guidance
actually works on a real project. Run all six scenarios below against
a version before calling it stable; record the outcome of each in this
project's own session log.

## Scenario 1: Retroactive hackathon replay

This scenario references the author's own original development-reference
project as a concrete example; other maintainers of this package should
substitute a project of their own with a similar shape (existing
requirements doc, no prior SIA history) when running this checklist.
Point a fresh assistant session at `C:\Users\Bot\Desktop\hackerrank\buyorwait`'s
`requirements.md`/`problem_statement.md`, with only `sia/` available (no
Superpowers plugin, no prior context). Confirm it reconstructs an
`AGENT.md`, spec, and plan structure equivalent in substance to the ones
that session actually produced by hand.

## Scenario 2: Brownfield software

Run against an existing repo with a bug-fix-shaped ask. Confirm intake
correctly classifies it as brownfield software, `guides/security-gate.md`
loads, and the approval-gate severity table in
`guides/questioning-and-approval.md` is respected for anything at or
above medium severity. Repeat Intake once for each of the three
existing-project modes: bounded repository exploration, goal-first with
no broad scan, and conversational discovery. In every case verify that
the recorded knowns and unknowns match files actually read.

## Scenario 3: Non-software project

Run against a document/deck-prep or design-work ask (an RFP or a design
mockup request). Confirm the security gate does *not* load, and that
the generated project `AGENT.md`'s definition of done is
reviewer-sign-off-shaped, not test-shaped.

## Scenario 4: second host

Run the same intake + spec-authoring flow on any assistant other than
Claude Code. Confirm the guides in `guides/` read as actionable
instructions there too — no phrasing that only makes sense as a
Claude-specific tool call.

## Scenario 5: Convergence over time

Run a longer-lived scenario across several plan phases on one project.
Confirm the deviation rate (`capture-interface.md`'s Convergence
Signal) actually falls across phases — not just that DEVIATIONs get
logged, but that the same class of mistake stops recurring once a rule
for it exists in that project's `AGENT.md`.

## Scenario 6: Generated skills and auditable delegation

In a fresh project, install SIA and give the assistant only the standard
entry instruction. Verify that it asks for or finds the project goal,
generates a project operating skill and `sdd/skill-manifest.md`, then
creates a task brief, host dispatch record, subagent report, reviewer
verdict, and progress entry for a real implementation task. A run that
implements task-owned code directly while the host can spawn subagents
fails this scenario even if its tests pass.

## Scenario 7: Optional attribution

Run four fresh Intake conversations and select `none`, `README badge`,
`commit trailers`, and `both` once each. Confirm `none` causes no README or
commit-message change; badge modes preserve existing README style and require
approval; trailer modes preserve the human Git identity and use a real,
committed `SIA-Run` evidence path. Confirm the generated project `AGENT.md`,
project skill, and skill manifest record the selected mode.
