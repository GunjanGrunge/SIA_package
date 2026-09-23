# SIA Runtime Workflow Contract

Run `sia next --json` at the start of every SIA turn and after context
compaction. Persisted `.sia/` state is the source of workflow position.

## Universal Rules

- User instructions and explicit approvals are highest authority.
- Respect runtime mode, stage ownership, bridge policy, budgets, and active
  feedback rules.
- Never replace BMAD, Superpowers, MCP, native skills, or other framework files.
- Persist evidence before advancement; conversation claims are not evidence.
- Record PASS/DEVIATION outcomes and run preflight before related work.

## Cost-Aware Multi-Agent Execution

Only orchestrator mode at SIA-owned execution may launch workers. Configure
exact cheap/current/strong model IDs, configured prices, hard token/USD
ceilings, warning fraction, concurrency, and optional standalone command arrays
with `sia orchestrate configure`.

Prepare each task with disjoint owned files, risk, complexity, and an optional
token estimate. Create one immutable dispatch plan:

- `native-host`: the active coding assistant launches native subagents from the
  plan and submits caller-attested receipts;
- `standalone`: SIA launches explicitly approved argument-array workers with
  `shell=False`, bounded output, timeout, and minimal environment inheritance.

Route simple low-risk work to cheap, normal work/review to current, and
complex/high-risk work or high-risk review to strong unless the approved config
says otherwise. Run independent implementers in parallel, then independent
reviewers. Never infer model IDs or label estimated/calculated usage as actual.
Stop at hard budgets and preserve plugins as capabilities rather than alternate
state stores.

## Evidence And Integration

Every receipt names the immutable plan hash, operation, worker identity,
requested/actual model, report path, provenance, and telemetry quality. The
controller never edits dispatched files. Integration requires every operation
to complete, separate reviewer identity, a full suite/interface/combined-diff
check, and an evidence manifest binding plan and receipt hashes.

Standalone child processes run with the current user's permissions and are not
a filesystem/network sandbox. Native host IDs remain attestations unless the
host provides verifiable metadata.
