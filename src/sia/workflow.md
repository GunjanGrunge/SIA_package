# SIA Runtime Workflow Contract

Use `sia next --json` at the beginning of every SIA turn and after context
compaction. The returned stage is the durable source of workflow position.

## Universal Rules

- User instructions and explicit approvals are highest authority.
- Respect `.sia/config.json` stage ownership and `framework_policy`.
- In bridge mode, do not edit or delete BMAD, Superpowers, or other framework
  files. Keep their skills/plugins available in parallel.
- Persist artifact evidence before `sia advance`; a chat claim is not evidence.
- Record every proposal outcome with `sia record` or `sia capture`, and run
  `sia preflight` before the next proposal.

## Stages

Intake classifies the work and competing tooling. Spec creates an approved
contract. Project instructions capture only project-specific durable rules.
Skills create a project operating skill and `sdd/skill-manifest.md`. Plan names
exact file ownership, interfaces, checks, and integration. Execution prepares
one brief per task, dispatches a real host-native agent, records its native ID,
attaches an independent review, and finishes with combined integration
evidence. Feedback records outcomes, rules, and convergence.

## Execution Boundary

The controller coordinates and reviews; it does not edit task-owned files after
dispatch. Independent tasks with disjoint file ownership may run in parallel.
Overlapping ownership must be sequenced or assigned to a later integration
task. If the host lacks native subagents, switch to planning/advisory mode or
ask the user to approve a manual handoff; never fabricate dispatch evidence.
