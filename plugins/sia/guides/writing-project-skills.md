# Writing Project-Specific Skills

Generate these only after Intake, the approved spec, and the project's own
agent instructions exist. A project skill is a thin, evidence-derived operating
contract; it is not a copy of SIA's generic guides.

## When To Generate

Generate or refresh skills after the project contract changes. Never infer a
host or install an adapter without the user's choice. In coexistence mode,
identify BMAD, Superpowers, and other agent tooling and leave their files and
workflow ownership untouched.

## Output Locations

Keep the canonical project skill under `skills/<project-slug>-sia/SKILL.md`.
Install host discovery copies only through `sia adapter install --host <host>`.
Record every canonical skill and adapter in `sdd/skill-manifest.md`. Never
replace an existing host file: use a namespaced SIA path or stop on collision.

## Required Contents

Every project-specific skill must state:

- its project goal and links to the approved spec and plan;
- the selected SIA mode: `advisory`, `planning`, or `orchestrator`;
- the artifact ownership boundary between SIA and other frameworks;
- the exact validation commands and definition of done;
- applicable accumulated feedback rules and their provenance;
- the Execution gate: prepare a task, dispatch a real host-native subagent,
  record host evidence, obtain a separate review, and complete integration;
- `sia next --json` as the durable re-entry point after a new session or
  context compaction.

Do not put secrets, provider tokens, or a duplicated generic SIA pipeline in a
skill.

## Skill Manifest

Write `sdd/skill-manifest.md` with one row per skill or adapter: logical name,
path, host, evidence sources, generated timestamp, SIA mode, and owner. Include
competing frameworks discovered at Intake and the stages they own. This makes
parallel plugin use explicit rather than relying on whichever prompt loaded
last.

## Modular Skill Decomposition And Attribution

Generate one core operating skill plus only evidence-justified feature/domain
skills. Goal-first or conversational intake limits skill generation to the
confirmed goal and evidence actually read; do not invent a broad pack. Refresh
execution-facing skills after the approved plan changes. Every skill records
its purpose, evidence, runtime mode, stage owner, relevant standing rules,
exact checks, and attribution policy. Host discovery copies are selected by the
user/host, namespaced, collision-safe, and distinct from the generic SIA
launcher adapter.

Extend the manifest with each canonical path, host copy, purpose, evidence,
generation reason/time, owner, competing framework stages, attribution mode,
README path, and reviewer note. Prefer a small modular pack over a monolithic
context dump.
