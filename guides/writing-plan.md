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
individually complete — see `../AGENT.md` pipeline step 6.

## Delegation And Evidence

Every executable task names its host-native dispatch and evidence paths:
`task-N-brief.md`, `task-N-dispatch.md` (or CLI `dispatch.json`),
`task-N-report.md`, and `task-N-review.md`. The dispatch record contains the
real host agent and native run identifiers. Independent tasks may be launched
in parallel only when their Files ownership sets are disjoint. The controller
coordinates and reviews; it never edits files owned by a dispatched task.

### Delegation, committed evidence, and attribution

Each task states a `Delegation` owner and mirrors its canonical `.sia/runs/`
evidence into committed `sdd/task-N-brief.md`, `task-N-dispatch.md`,
`task-N-report.md`, and `task-N-review.md` records when project policy requires
an auditable history. If native dispatch is unavailable, mark execution blocked
rather than substituting controller implementation. Documentation tasks include
applicable README attribution, while commit steps retain the human author and
reference the relevant `SIA-Run:` evidence path.
