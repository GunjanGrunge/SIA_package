# Host Integration Contract

SIA has one durable control plane: the `sia` CLI and project-local `.sia/`
state. Host files are opt-in launchers, not alternate implementations.

## Modes

| Mode | SIA owns | Use with other frameworks |
|---|---|---|
| `advisory` | feedback capture, rules, preflight, convergence | BMAD/Superpowers own planning and execution |
| `planning` | intake, spec, project instructions, skills, plan | another framework may own execution |
| `orchestrator` | full pipeline and execution evidence | SIA dispatches; other plugins remain available as tools/skills |

`bridge` is the default framework policy. SIA never edits or deletes another
framework's files and writes runtime data only below `.sia/`. Assign stage
ownership with `sia owner --stage <stage> --to <sia|bmad|superpowers|name>`;
`sia next` exposes the current owner and requires that owner's artifact before
advancement.

## Re-entry Protocol

Every host launcher performs the same operation:

1. Run `sia next --json` from the project root.
2. Follow the returned current stage and mode.
3. Before implementation, run `sia task prepare` with exclusive file owners.
4. Spawn the host's real native implementer/reviewer agents.
5. Record native agent/run identifiers with `sia task dispatch` and attach the
   report/review with `sia task finish`.
6. Record PASS/DEVIATION outcomes. Run `sia preflight` before the next proposal.

This state survives fresh chats and context compaction, so SIA does not depend
on remaining in the model's conversation window.

## Adapter Locations

- Claude Code: `.claude/skills/sia/SKILL.md` (`disable-model-invocation: true`)
- Codex: `.agents/skills/sia/SKILL.md`
- Kiro: `.kiro/steering/sia.md` (`inclusion: manual`)
- Antigravity: `.agents/workflows/sia.md`

Install with `sia adapter install --host claude|codex|kiro|antigravity`.
Adapters refuse to overwrite existing files. They do not install hooks because
a prompt/session hook would make SIA monopolize unrelated work.

## Native Subagents

SIA checks the ordering and completeness of caller-attested dispatch evidence; it
does not authenticate a vendor's agent API. The host launcher/controller must
supply truthful native identifiers. Claude, Codex, Kiro, and Antigravity each
spawn agents through their native harness. If a host cannot provide native subagents, use `planning` or
`advisory` mode, or explicitly perform manual task handoffs; do not claim
multi-agent execution occurred.
