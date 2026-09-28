# Writing Project-Specific Skills

A project-specific skill teaches the agent, its subagents and any collaborating plugin
how to do one kind of work **this project's requirements call for**, using this
project's real commands, paths and conventions. SIA writes them; the user never
designs the pack by hand. They are not copies of SIA's generic guides, and they
are never generated from a catalog: a skill exists because a requirement asks
for the capability.

## When To Generate

At the `skills` stage, after intake, the approved spec and the project's own
agent instructions exist. Refresh them when the plan or spec changes: update a
skill whose requirement changed, write one for a new requirement, retire one
whose requirement was dropped.

1. Call `sia_skill_context` (`sia skill context`). It returns the requirement
   sources (intake, spec, project-instructions and plan evidence, plus
   AGENTS.md/CLAUDE.md/AGENT.md/GEMINI.md), dependencies and layout, the skills
   and frameworks already installed, and the active rules.
2. Read every requirement source. List the distinct capabilities the
   requirements demand. For example, a spec that says "track training loss and
   validation accuracy after every epoch" demands a loss-and-accuracy
   monitoring skill; a spec for a REST service that says "every endpoint is
   rate limited" demands a rate-limiting skill. Different projects produce
   entirely different packs.
3. Drop any capability an existing project skill or installed framework already
   covers. Superpowers already covers TDD, debugging and verification: a
   project skill points to those (`superpowers:test-driven-development`)
   instead of restating them.
4. Write each remaining capability with `sia_skill_write`, one call per skill.
5. Advance with `sdd/skill-manifest.md` as evidence.

Dependencies and layout tell you *how* to do the work (the real test command,
the real metrics file), never *what* work to do. A dependency on a library is
not a requirement.

## Output Locations

`sia_skill_write` installs each skill where hosts discover project skills:
`.claude/skills/<name>/SKILL.md` (Claude Code) and
`.agents/skills/<name>/SKILL.md` (Codex); pass `hosts` to limit it. SIA keeps
a registry in `.sia/skills.json` and regenerates `sdd/skill-manifest.md`.

SIA never overwrites a skill it did not write, and stops updating a SIA skill
the user edited by hand. Choose another name on collision.

## Required Contents

Each call supplies:

- `name`: kebab-case, specific (`loss-monitoring`, not `ml`);
- `description`: what it does and `Use when ...`, so hosts trigger it;
- `body`: the instructions, meaning steps, exact commands, files to read or
  write, checks, and the definition of done for this capability;
- `requirements`: one or more `{source, quote}` pairs. The quote must appear
  verbatim (line breaks aside) in a requirement source, or SIA refuses the
  skill;
- `paths`: globs the skill applies to, which selects the standing rules it
  carries.

SIA appends a "Why this skill exists" section with the cited requirements and a
standing-rules block. The rules block is re-rendered whenever a rule is learned
or retired, so every skill keeps up with the user's corrections. The
Execution gate is unchanged: skills guide the work inside a task; they never replace
prepare, dispatch, independent review and integration. `sia next --json`
remains the re-entry point after a new session or compaction.

Do not put secrets, provider tokens, or a duplicated generic SIA pipeline in a
skill. SIA refuses text that looks like a credential.

## Skill Manifest

`sdd/skill-manifest.md` is generated: one row per skill with status, version,
hosts, paths, the requirement it serves and when it was updated, plus the
installed frameworks the pack complements. It is the evidence for advancing
the `skills` stage and makes parallel plugin use explicit rather than relying
on whichever prompt loaded last.

## Modular Skill Decomposition And Attribution

Prefer a small modular pack, one skill per capability, over a monolithic
context dump. Every subagent is told at spawn which project skills exist, so a
skill that is too broad gets loaded for work it does not fit. Record
attribution per `guides/attribution.md`.
