# Subagent Task Brief, Report, and Progress Log Formats

Used during the Execution stage (`../AGENT.md` pipeline step 6). Spawn
one scoped subagent per plan task, using whatever subagent mechanism
your host provides — SIA does not assume a specific tool call or API,
only that the host can hand a subagent a self-contained brief and get a
report back.

## Task Brief Format

Give the subagent only what its task needs, not the whole plan:

```text
# Task Brief: <task name>

Goal: <one sentence>
Files: <exact paths to create/modify, from the plan's Files block — this
        is the task's exclusive ownership boundary; touching any file
        outside this list is itself an escalation, not a bonus>
Interfaces: <exact names/signatures this task consumes and produces,
             from the plan's Interfaces block>
Steps: <the plan's Steps block for this task, verbatim>
Acceptance Criteria: <how the reviewer will verify this task is done —
                       usually "the task's own test/check passes">
Effort Budget: <an expected ceiling — e.g. a tool-call count, a token
                budget, or elapsed time — appropriate to the task's size.
                Exceeding it is itself a signal to stop and report
                blocked/partial with what was tried, not a reason to push
                harder.>
Relevant Standing Rules: <any Accumulated Feedback Rules from the
                           project's AGENT.md that plausibly apply to
                           this task's Files/scope, copied in verbatim —
                           not "check AGENT.md yourself." A subagent
                           given only its own task has no reason to read
                           the whole project file; the rules that matter
                           for this specific task must travel with the
                           brief, or the pre-flight self-check
                           (`../capture-interface.md`) has nothing to
                           check against at the subagent level. If none
                           apply, say so explicitly ("none apply to this
                           task's files") rather than leaving the field
                           blank — a blank field looks skipped, not
                           checked.>
Escalate, don't improvise, when: <the fixed list below>
```

**The fixed escalation list** (include verbatim in every brief, not
paraphrased per-task): stop and report back rather than working around
any of the following — an unexpected dependency the brief didn't
mention; a file the brief didn't list needing changes; a conflicting or
already-modified file; a requirement in the brief that's ambiguous
enough to support two different implementations; a missing tool,
credential, or piece of environment the task needs; a test that fails
for a reason unrelated to this task's own change; or the Effort Budget
being exceeded with the task still incomplete. In every one of these
cases, report status `blocked` (see Task Report Format) with exactly
what was found — improvising past any of them is scope creep even when
the improvisation would probably work.

## Task Report Format

The subagent returns, after completing (or getting stuck on) its task:

```text
# Task Report: <task name>

Status: complete | blocked | partial
What changed: <files touched, one line each>
Verification evidence: <the actual command run and its output, not a
                         claim that it passed>
Deviations from the brief: <anything done differently than specified,
                             and why>
Open questions: <anything the reviewer needs to decide>
```

A report claiming "done" without verification evidence is incomplete —
send it back rather than marking the task reviewed.

## Progress Log Format

One shared file per plan run (e.g. `sdd/progress.md`), appended to after
each task's report is reviewed:

```text
## Task N: <name> — <complete|blocked|reverted> — <ISO-8601 timestamp>
Report: <path to task-N-report.md>
Reviewer notes: <anything the reviewer added beyond the report itself>
Usage: <token counts if the host exposes them, else turns/spawns/files-touched>
```

## Integration Report Format

After every task in the plan is individually reviewed complete, run the
Integration phase (`../AGENT.md` pipeline step 6) and record it in the
same progress log:

```text
## Integration — <complete|blocked> — <ISO-8601 timestamp>
Full suite run: <the actual command and its output — not "tests pass">
Cross-task interfaces checked: <each Interfaces contract from the plan,
                                 confirmed to match in the combined code>
Combined diff reviewed: <yes/no — the whole plan's diff as one unit,
                          not each task's diff in isolation>
Standing rules checked: <every Accumulated Feedback Rule whose scope
                          plausibly covers anything in the combined
                          diff, with a per-rule verdict — a task-level
                          check can miss a rule that only becomes
                          relevant once every task's code coexists>
Issues found: <anything only visible once every task's code coexists>
```

A plan is not done when its last task is reviewed complete — it is done
when the Integration entry above is also `complete`.

## Review Before Marking Complete

Diff every subagent's changes before marking its task complete. Route
anything at or above medium severity (see `questioning-and-approval.md`)
through the user, even if the subagent's own report claims success.

The reviewer's own output must answer two separate questions, not just
one: **did the code work** (spec compliance, quality — the usual review
criteria), and **did this repeat a known mistake** — explicitly state
which of the task brief's Relevant Standing Rules were checked against
the diff, and the verdict for each (respected / violated / not
applicable to what this diff actually touched). A reviewer report that
only answers the first question has silently skipped the second — the
Integration Report Format below carries the same requirement at the
whole-plan level.

## Execution Gate

Before implementation, persist the brief with `sia task prepare`. Invoke the
host's real subagent mechanism and immediately record **Host Evidence** with
`sia task dispatch`: host name, agent ID, and native run ID. These identifiers
are caller-attested because SIA cannot authenticate every vendor harness; never
fabricate them. A prompt copied
into the controller's own context is not a dispatch. After dispatch, the
controller does not implement task-owned files itself.

Completion requires an implementer report and a separately authored reviewer
verdict attached by `sia task finish`. Disjoint ownership permits parallel
agents; overlapping ownership requires sequencing or an integration task.
After all tasks are reviewed, `sia integration` records the combined suite,
interface checks, standing-rule checks, and whole-diff review.
