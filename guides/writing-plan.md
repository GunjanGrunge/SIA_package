# Writing A Project's Own Implementation Plan

Authored after that project's spec (`writing-spec.md`) is approved,
before any subagent starts executing. Assume whoever executes a task has
no memory of this plan-writing session and no context beyond their own
task — write accordingly.

## Task Structure

Each task in the plan states:

- **Files** — exact paths to create or modify, with line ranges for
  modifications to existing files. This list is also that task's
  **ownership boundary** (see Owned Files below) — not just a preview.
- **Interfaces** — what this task consumes from earlier tasks (exact
  names/signatures) and what it produces for later tasks to rely on.
  A task's executor sees only their own task; this is how they learn
  the names and shapes neighboring tasks use.
- **Steps** — the actual ordered actions, each one small enough to do
  in a few minutes (see Bite-Sized Steps below), each containing real
  content, not a description of content.

A task is the smallest unit that carries its own verification step and
is worth a fresh reviewer's gate — split only where a reviewer could
reasonably approve one task while rejecting its neighbor.

## Owned Files

Two subagents must never silently modify the same file. Each task's
**Files** block is that task's exclusive ownership boundary for the
lifetime of its execution — no other task, and no task running
concurrently with it, may touch a file another task owns.

When two tasks genuinely need to change the same file:

- **Prefer sequencing.** Make the later task depend on the earlier one
  (its Interfaces block should name what changed and why), so the file
  is only ever owned by one task at a time.
- **If truly simultaneous changes to one file are unavoidable**, do not
  split ownership silently — add a dedicated, later **integration task**
  whose only job is reconciling that file, with the other two tasks
  explicitly forbidden from touching it and instead producing their
  changes as a patch/diff the integration task applies. Name this in the
  plan; don't leave it implicit.

A plan's Self-Review (below) must include checking that no two tasks'
Files blocks overlap, unless an integration task exists specifically to
own that overlap.

## Delegation And Evidence

Every implementation task must name a **Delegation** field: normally
`scoped implementer subagent`; only orchestration, review, or a named
integration task may be `controller-owned`. Controller ownership is not
a loophole for writing task-owned production files.

Before a task's code is changed, the controller creates a durable
artifact set under `sdd/` (or an equivalent committed project directory):

- `task-N-brief.md` — the exact self-contained brief sent to the host;
- `task-N-dispatch.md` — host mechanism, subagent identifier/name, and
  dispatch timestamp; and
- `task-N-report.md` — the subagent result plus a reviewer verdict.

The plan must name this artifact root and reserve the final Integration
entry in its progress log. If the host cannot actually dispatch a
subagent, execution is blocked and the user must be told; do not quietly
perform the task as the controller and label it delegated.

When the owner's selected SIA attribution mode includes a README badge, make
that a named documentation task with exclusive ownership of the README and
any approved asset path. When it includes commit trailers, record the exact
trailer format and `SIA-Run` evidence path in the plan's commit step. Follow
`attribution.md`; never add branding or alter a Git author by default.

## Bite-Sized Steps

One action per step:

1. Write the failing test (or, for non-code deliverables, the check
   that proves the deliverable is missing/incomplete).
2. Run it, confirm it fails, and confirm *why* it fails.
3. Write the minimal content/code to satisfy it.
4. Run it again, confirm it passes.
5. Commit.

## No Placeholders

Never write "TBD", "add appropriate handling", "similar to Task N", or
a step that describes what to do without showing the actual content.
If a task needs a type or function defined in another task, name it
exactly as that task's Interfaces block does.

## Self-Review Before Handing Off

After the full plan is written, check it against its spec once:
every spec section maps to at least one task; no placeholders remain;
names/signatures used in later tasks match what earlier tasks' Interfaces
blocks promised; no two tasks' Files blocks overlap unless a dedicated
integration task owns that overlap (see Owned Files above). Finally,
confirm the plan ends with an Integration phase after every task is
individually complete — see `../AGENT.md` pipeline step 7. Also confirm
that every implementation task has a Delegation field and durable
subagent-evidence paths.
