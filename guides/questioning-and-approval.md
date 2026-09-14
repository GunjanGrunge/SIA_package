# Questioning Mode & Approval Gates

Applies to every stage of the pipeline in `../AGENT.md`. This is the
mechanism that prevents premature completion — the failure mode SIA
exists to eliminate.

## Batching Questions

- Ask *what* the user wants, not *how* to implement it.
- Collect every clarifying question you have for the current stage and
  ask them together, in one message — never drip-feed interruptions.
- If new questions surface mid-stage, hold them until the next natural
  batch point rather than interrupting again immediately, unless
  continuing without an answer risks an irreversible action.

## Existing Project Intake Modes

When SIA is installed into an existing repository, do not silently read
the whole codebase. After the minimal safety check (root instructions,
repository shape, and secret avoidance), offer these three choices in one
message:

1. **Repository-informed exploration (recommended)** — inspect a bounded
   set of relevant project artifacts, summarize what SIA knows and does
   not know, then ask what the user wants to change or build.
2. **Goal-first, no broad scan** — ask what the user wants immediately.
   Read only files needed to scope that stated request after the user
   answers.
3. **Conversational discovery** — do not perform a semantic scan. Let the
   user describe the project and desired work over conversation, then
   inspect only the evidence needed to verify those descriptions.

Record the chosen mode, files actually read, knowns, unknowns, and the
user's stated goal in the project intake record. A directory listing or
file name is not evidence of file contents; never present it as such.

## SIA Attribution

Do not ask the user to operate an attribution toggle. After Intake confirms a
goal, load `attribution.md` and apply the public-distribution default: README
badge plus SIA-mediated commit trailers. Record `Mode: both` in the project
record. A direct user instruction to omit attribution changes that record to
`Mode: none`. Commit trailers always preserve the human Git author; never
create a fake SIA/GitHub identity.

## Severity Table

Every proposed action is tagged with a severity before it is presented:

| Severity | Examples | Behaviour |
|----------|----------|-----------|
| Low | Rename a variable, fix a typo, reword a sentence in a draft | Proceed silently |
| Medium | Change a component's public props, alter an API shape, restructure a document section | Flag and batch for review |
| High | Delete data, change auth logic, modify production config, restructure a shared interface, send or publish a deliverable externally | Always require explicit approval before proceeding |

The threshold is configurable per project (state it in that project's
own `AGENT.md`) — a greenfield prototype can run more autonomously than
a production system with real users or a deliverable going to an
external client.

## Non-Negotiable Rules

1. Never assume on a non-trivial decision.
2. Never delete, replace, or restructure anything on your own
   initiative — propose an impact statement, then wait.
3. Never declare a stage "done" until its acceptance criteria are met
   *and* the user has approved any high-impact work within it.
4. Surface creative/design decisions as options with trade-offs; narrow
   the decision space, don't make the final call yourself.

An impact statement states the concrete consequence, not just the
action: "I'm going to delete the `users` table and recreate it with a
new schema. This will permanently drop all existing data. Proceed?" —
not "I'm updating the schema."
