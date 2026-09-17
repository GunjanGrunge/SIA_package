# Generating Project-Specific Skill Files

SIA is a generator. After it learns the user's goal, confirms the
project shape, and writes the project's own `AGENT.md`, it must create
the skill files that let the coding host reliably re-enter that project
context in later sessions. The user installs SIA and states a goal; the
user does **not** have to design an agent-skill pack. These are
project-specific skills, derived from the project rather than selected
from a fixed template library.

## When To Generate

Generate a foundation skill immediately after project `AGENT.md`
authoring. Once the implementation plan is approved, generate or extend
an execution skill that names the plan's delegation and evidence gate.
Regenerate only when the approved spec, plan, or active standing rules
change materially; record why rather than silently overwriting a skill.
For an existing repository, derive the skill only from the selected
intake mode's actual evidence. A goal-first or conversational intake
must preserve unknowns rather than inventing a repository model.

## Output Locations

Write a host-neutral source copy to:

```text
skills/<project-slug>-sia/SKILL.md
```

Then place the same project-generated skill where the active host
discovers skills. For Claude Code this is:

```text
.claude/skills/<project-slug>-sia/SKILL.md
```

Other hosts use their own discovery location. Keep the project skill
committed; only the vendored `sia/` package is normally ignored.

## Required Contents

Each generated project skill must contain:

1. **Purpose and trigger** — the project goal and when this skill must
   load.
2. **Provenance** — exact paths to the approved spec, project `AGENT.md`,
   plan, and the date/reason it was generated.
3. **Authority and scope** — it defers to user instructions and the
   project `AGENT.md`; it does not silently broaden the goal.
4. **Project-derived operating rules** — only rules evidenced by this
   project (stack, constraints, acceptance checks, or active feedback
   rules), not a copied generic domain pack.
5. **Execution gate** — implementation tasks require a brief, dispatch
   record, subagent report, reviewer verdict, and progress entry. The
   controller must not implement task-owned files when the host supports
   subagents.
6. **Human gates and reporting** — where approvals, status, usage, and
   integration evidence are recorded.
7. **Attribution policy** — state the public-distribution default, `both`,
   from `attribution.md`, or `none` only when directly overridden by the user.
   Include the exact trailer format, explain that it applies only to
   SIA-mediated commits while preserving human Git identity, and name the
   README badge path.

## Modular Feature Skill Decomposition

SIA derives a **Modular Skill Pack** composed of focused, feature-specific skill files rather than a single monolithic dump. During intake and spec analysis, SIA identifies the distinct functional modules and domain components of the project.

For example, a web project with theme settings and product search is decomposed into:

1. **Core Operating Skill** (`skills/<project-slug>-core/SKILL.md`) — project authority, main workflow contract, and execution safety gate.
2. **Feature/Domain Skills** (`skills/<project-slug>-<feature>/SKILL.md`), such as:
   - `skills/<project-slug>-theme-manager/SKILL.md` (color schemes, theme state rules, UI tokens)
   - `skills/<project-slug>-product-search/SKILL.md` (search queries, indexing, product schema rules)
   - `skills/<project-slug>-auth-handler/SKILL.md` (authentication, session limits, security constraints)

These modular skills enable **Cross-Engine Collaboration**: because skills follow standard markdown formats placed in `skills/` and host discovery folders (`.claude/skills/`, `.agents/skills/`), the exact same feature skills can be loaded and shared across Claude Code, Codex, Antigravity IDE, Cursor, and other AI coding assistants working on the project.

## Skill Manifest

Create `sdd/skill-manifest.md` alongside the execution records. For each
generated skill record its path, purpose, project evidence used,
host-discovery copy (if any), generation timestamp, and reviewer note.
The manifest makes project adaptation auditable and distinguishes a
generated skill from a static SIA guide.
Record the default/overridden attribution mode and README path as part of the
same manifest entry.

## Quality Rules

- Synthesize focused, modular feature skills for every distinct domain component identified in the spec.
- Do not dump everything into a single monolithic skill file; decompose feature-specific operating rules so subagents and multi-engine collaborators load only the relevant feature context.
- Do not duplicate the full `AGENT.md`. Link to it as the authority and include only the task-relevant derived instructions.
- Never place secrets, tokens, or copied `.env` values in a skill.
- A missing project-skill manifest or missing execution gate is a
  DEVIATION, not cosmetic documentation debt.
