# Installing SIA Into A Project

SIA is not a plugin you install once globally — it's a folder you copy
into each project you want to use it with, the same way BMAD's
`.claude/skills/` and `_bmad/` folders are vendored per-project rather
than installed centrally.

## 1. Copy the package

```bash
git clone https://github.com/GunjanGrunge/SIA_package.git /path/to/your-project/sia
```

(Or download the ZIP from GitHub and extract it as `sia/` in your
project root — either way, the folder you end up with must be named
`sia/`, since every guide in this package refers to itself by that
relative path.)

## 2. Gitignore the vendored package, keep the generated artifacts

`sia/` is vendored tooling — it is not part of the target project's own
content, the same way BMAD's `.claude/` and `_bmad/` folders aren't part
of the application they help build. Add this to the target project's own
`.gitignore`:

```gitignore
# Vendored SIA (Self Improving Agents) tooling — not part of this project.
sia/
```

Do **not** gitignore what SIA *generates* for this project — that
project's own `AGENT.md`, `docs/specs/`, `docs/plans/`, `logs/sessions/`,
generated `skills/`, host-discovery skill copies, and any `sdd/`-style
subagent task-brief folders are real project history
and should be committed, the same way BMAD's `_bmad-output/` (a project's
own generated brainstorm/intent record, not vendored tooling) is kept and
committed rather than ignored.

## 3. Give your host a way to find `sia/AGENT.md`

SIA has no host-specific auto-discovery of its own — `sia/AGENT.md` is the
one mandatory read, and by default nothing points a host at it
automatically. Two ways to close that:

- **Tell the assistant once, explicitly**, at the start of a session:
  "Read `sia/AGENT.md` and follow it." This always works, on any host,
  and requires copying nothing extra.
- **If your host is Claude Code**, also copy
  `sia/integrations/claude-code/SKILL.md` to `.claude/skills/sia/SKILL.md`
  in the target project. This is a thin shim — a few lines, no logic of
  its own — that only exists so Claude Code's own skill-discovery finds
  SIA without being told. It always defers to `sia/AGENT.md` as the
  actual source of truth; if the two ever disagree, `sia/AGENT.md` is
  correct. `.claude/skills/` is discovered by Claude Code regardless of
  `.gitignore` status, matching how BMAD's own `.claude/skills/bmad-*`
  folders work while still being gitignored.

Other hosts may grow their own equivalent shims over time
(e.g. a `.cursor/rules/sia.md`, or an `AGENTS.md`-style pointer) — each
would be a similarly thin, static file added under
`sia/integrations/<host>/`, never a fork of SIA's actual guidance.

After Intake and project `AGENT.md` authoring, SIA generates the
project's own skill(s) under `skills/` and, for Claude Code,
`.claude/skills/<project-slug>-sia/SKILL.md`. Those are committed project
artifacts, not files the user must hand-write. The generic `sia` shim is
only the launcher; the generated skill carries the project's specific
goal, rules, and execution gate.
