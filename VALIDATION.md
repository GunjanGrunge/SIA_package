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
above medium severity.

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

## Scenario 7: Default public attribution

Run a public project flow without mentioning attribution. Confirm the README
record and future SIA-mediated commit trailers follow `guides/attribution.md`,
retain the human Git author, and include `Assisted-by: SIA` plus `SIA-Run:`.
Repeat with an explicit user request to omit attribution and confirm it is
respected and recorded.

## Scenario 8: Persistent runtime and safety boundaries

Install the built wheel in a clean environment and exercise all three runtime
modes. Confirm `sia next --json` survives a fresh process; advancement rejects
missing evidence; task ownership rejects root escape, parent/child overlap,
and Windows case aliases; reviewer identity differs from implementer identity;
integration rejects unfinished or stale task sets; concurrent state mutations
serialize; adapters refuse collisions and redirected paths; and `sia guide`
contains every required policy file, including attribution.
