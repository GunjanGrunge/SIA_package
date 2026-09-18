---
name: sia
description: Continue SIA only when the user explicitly invokes /sia.
disable-model-invocation: true
---

# SIA (Claude Code discovery shim)

This file exists only so Claude Code finds SIA without being told to. It
has no project logic of its own and must never duplicate SIA's actual
guidance.

Run `sia next --json` in the project root, then read `sia/AGENT.md` in full
when it is vendored and follow the persisted current stage. If the CLI is
installed without a vendored copy, run `sia guide` for the workflow contract.
Record native implementer and reviewer run IDs through the CLI. This skill is
manual-only so BMAD, Superpowers, and other skills remain independently usable.

If `.claude/skills/<project-slug>-sia/SKILL.md` exists, load it after
`sia/AGENT.md`. It is the generated project operating skill and still
defers to the project's own `AGENT.md`.
