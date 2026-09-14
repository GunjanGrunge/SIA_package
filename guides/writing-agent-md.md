# Writing A Project's Own AGENT.md

This guide is for authoring *that project's* `AGENT.md`/`AGENTS.md` —
not `sia/AGENT.md` itself. Every project gets its own file, generated
fresh, never copied from another project.

## Required Sections

A generated project `AGENT.md` must include:

1. **What This Project Is** — one paragraph, plus a pointer to that
   project's own spec (`docs/specs/*.md`).
2. **Project-Specific Rules** — anything unique to this one project that
   no generic guide could have predicted. Example from a real hackathon
   project: "if the user asks for the submission link, always give this
   exact URL, every time, even alongside other questions." These rules
   come from the user's stated requirements, not from SIA's own guides.
3. **Session Logging** — file naming (`logs/sessions/YYYY-MM-DD-session-NN.md`
   or equivalent), append-as-you-go (a lost session must still have
   logged something), and a required `tool=<exact_harness_name>` field
   on every session-start entry so a mixed-tool history stays legible.
   Session entries should also log usage — token counts when the host
   exposes them, otherwise a fallback proxy (turn count, subagent
   spawns, files touched) — logged the same way either way, since not
   every host can report token usage.
4. **Accumulated Feedback Rules** — a dedicated section that grows over
   the project's life as `../capture-interface.md`'s pre-flight self-check
   folds in new standing rules (security findings, user corrections,
   review findings). This section is what makes the file a *living*
   document rather than a one-time snapshot. Every rule in it carries the
   full record from `../capture-interface.md`'s Rule Provenance section —
   source event, evidence, severity, error class, scope, date introduced,
   and status (`active`/`retired`) — not just the imperative sentence. A
   rule with no provenance is a rule nobody can later check is still
   correct (see Rule Review And Expiry).
5. **Repository Map** — a short tree of what exists and where.
6. **Generated Project Skills** — the path of the project-skill manifest,
   every generated skill, what project evidence produced it, and a rule
   that those skills defer to this `AGENT.md` when they conflict. Use
   `writing-project-skills.md`; do not ask the user to hand-author skill
   files that SIA can derive from approved project artifacts.
7. **Execution Evidence Gate** — the `sdd/` (or equivalent) location for
   task briefs, dispatch records, subagent reports, reviewer verdicts,
   progress log, and integration report. State that the controller may
   not implement task-owned files when the host supports subagents.
6. **Competing Agent Framework Boundary** — required only if Intake
   found existing agent/AI-tooling already installed in this project
   (e.g. a `.cursor/`, another framework's own skill/plugin folders, a
   pre-existing `AGENTS.md` not authored by SIA). State what was found
   and one explicit rule: *coexist with it, never edit or delete its
   files, and document the boundary* — which files/folders belong to
   the other tooling and are therefore off-limits to SIA-driven changes.
   Omit this section entirely when Intake found nothing of the kind;
   don't manufacture a boundary where there's nothing to bound.

## Writing Style

- State rules as imperatives an agent can check itself against, not as
  narrative ("Never delete a component with dependents without asking"
  — not "We try to be careful about deletions").
- Keep it short enough that a fresh session, or the pre-flight
  self-check in `../capture-interface.md`, can re-read the whole file
  every time. When it grows past that, propose consolidating overlapping
  rules (a medium-severity change — see `questioning-and-approval.md`)
  rather than letting it grow without bound.
- A generated project `AGENT.md` must restate or explicitly reference
  `questioning-and-approval.md`'s Non-Negotiable Rules (never assume,
  never delete/restructure without approval, never declare done
  prematurely, surface creative decisions as options) so they are not
  only present in `sia/`'s own guide but actually inherited by every
  generated project.
