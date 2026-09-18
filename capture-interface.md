# Feedback Capture Interface & Loop Engineering

This is SIA's self-improving layer: how a project accumulates fewer
mistakes over its own lifetime, not just a longer history of them.

## The Interface

```
capture(signal_type, context, severity, error_class)
```

- `signal_type` — free-text category, project-defined (e.g.
  `security-finding`, `user-correction`, `review-finding`,
  `spec-ambiguity`).
- `context` — what happened and where: a file/section reference, and
  the user's correction verbatim where one exists.
- `severity` — `low` / `medium` / `high`, the same scale as
  `guides/questioning-and-approval.md`'s severity table.
- `error_class` — a short, reusable label for *what kind* of mistake this
  is, distinct from `signal_type` (which is about where the signal came
  from). Reuse an existing class if this DEVIATION is the same kind of
  mistake as one already captured; only mint a new class when it
  genuinely isn't. Example classes: `unsafe-edit-target` (proposing to
  change something that shouldn't be hand-edited, e.g. a generated
  artifact), `missing-approval` (proceeding on a High-severity action
  without confirmation), `interface-assumption` (assuming a type/shape
  that turned out wrong), `unverified-claim` (asserting something works
  without the evidence to back it — see Rule Provenance below for why
  this class matters especially). This is what makes recurrence
  trackable *by kind of mistake*, not just as one undifferentiated rate
  (see Convergence Signal).

Every call appends a structured entry to that project's session log.
When the signal represents a standing rule ("don't delete components
without asking", "always sanitize this auth flow"), propose adding it
to that project's own `AGENT.md` under Accumulated Feedback Rules (see
`guides/writing-agent-md.md`), subject to the normal approval gate for
anything above low severity — recorded with the full provenance fields
below, not just the rule text.

## Rule Provenance

Every Accumulated Feedback Rule carries, not just the rule text itself:

- **Source event** — the specific session/experiment/task that produced
  it (a session-log reference, not "learned over time").
- **Evidence** — the actual `context` from the `capture()` call that
  produced it, quoted, not paraphrased.
- **Severity** — carried over from the originating `capture()` call.
- **Error class** — carried over from the originating `capture()` call.
- **Scope** — exactly what this rule governs (a file, a pattern, a
  category of action) — narrow enough that a future pre-flight check can
  actually tell whether a proposed change falls under it.
- **Date introduced.**
- **Status** — `active` or `retired` (see Rule Hygiene's expiry
  mechanism below). A retired rule stays in the file with its status
  changed, not deleted — deleting it would erase the provenance record
  of why it existed at all.

A rule missing any of these fields is incomplete — propose the complete
record, not just the imperative sentence, when adding one.

## PASS / DEVIATION

Classify every stage outcome as one of:

- **PASS** — the user approved without correction, verification/tests
  passed, review found nothing.
- **DEVIATION** — a user correction, a rejected proposal, a
  security-gate finding, a failed verification, a review finding.

Only DEVIATIONs are captured via the interface above. PASSes aren't
logged for their own sake, but they feed the Convergence Signal below.

### Process And Framework Deviations

Capture process failures as seriously as code failures. Examples include
skipping project-skill synthesis, a controller implementing a task that
should have been delegated, a missing dispatch record, or claiming token
budget compliance without host telemetry. Use a specific error class such
as `framework-default-override`, record the evidence, and turn the
correction into an active project rule before the next task.

## Pre-Flight Self-Check

Logging a DEVIATION is necessary but not sufficient — this step is what
actually makes the loop self-healing rather than a history nobody
re-reads. Before presenting the *next* proposal, spec section, plan, or
generated change:

1. Read that project's current `AGENT.md` Accumulated Feedback Rules
   section in full.
2. Check the work about to be presented against every rule there.
3. Silently self-correct anything that would violate a low-severity
   rule before showing the user anything.
4. For anything that would violate a medium/high-severity rule, state
   the conflict explicitly — e.g. "this would touch the auth flow
   flagged after the correction on 2026-09-10; proceeding needs your
   approval per that rule" — and route it through the approval gate.

## Convergence Signal

Compute a **deviation rate** (deviations ÷ total proposals) per
milestone or per week of active work, from the session log's PASS/
DEVIATION history — but compute it **per error class, not only as one
overall number**. An overall rate can look flat or falling while one
specific class of mistake (e.g. `unverified-claim`) keeps recurring
underneath it, masked by other classes improving. Track each class's own
count and trend.

This is not a score to game — it's a trend to show the user
periodically. A falling rate on a given class is evidence the rule
governing that class is working. A flat or rising rate on the *same
class* is itself worth raising directly with the user ("we've hit
`interface-assumption` deviations three times — worth revisiting the
spec instead of patching the code again?") rather than silently logging
a fourth entry. A single self-administered test run (one evaluator
writing both the rules and the test cases) will tend to show artificially
low deviation rates across every class — the strongest version of this
signal comes from real, independently-authored requests over real
elapsed sessions, not a single sitting's worth of self-designed probes.

## Rule Hygiene

Accumulated rules must stay small enough to actually be re-read at every
pre-flight check. When new rules overlap or supersede older ones,
propose consolidating them (merge, generalize, or retire a rule the
project has outgrown) rather than letting the list grow without bound.
Consolidation is a medium-severity change — it goes through the normal
approval gate, so the user always sees what's being merged or dropped
and why.

### Rule Review And Expiry

Rules do not stay correct forever — a codebase changes underneath them.
At a natural review point (a new plan's Spec-authoring stage is a good
default trigger, since it already re-reads project context), check each
`active` rule against current reality:

- **Still applies, unchanged** — leave it.
- **Superseded by a newer, more specific rule** — mark the old one
  `retired`, with a one-line pointer to what replaced it. Do not delete
  it (see Rule Provenance).
- **No longer applies** (the code/constraint it was about was removed or
  changed) — mark it `retired` with the reason, through the normal
  approval gate (this is itself a medium-severity change — retiring a
  rule silently is how a stale rule's *absence* becomes a surprise
  later).
- **Contradicts another active rule** — this is a Rule Hygiene failure
  that should have been caught at consolidation time; surface it to the
  user rather than silently picking a side.

A project's Accumulated Feedback Rules section should therefore be read,
in full, as "the currently active rules, plus a retired history below
them" — not assumed to be entirely live just because it's still in the
file.

## Executable Persistence

The installed CLI implements this interface across sessions. Use
`sia capture --signal <type> --context <text> --severity <level>
--error-class <class>` for a DEVIATION and `sia record --outcome pass ...` for
a PASS. Events append to `.sia/events.jsonl`; approved provenance-bearing rules
live in `.sia/rules.json`; `sia preflight` loads applicable active rules; and
`sia convergence` computes overall and per-error-class rates. This executable
record is the durable source for the prose loop above.
