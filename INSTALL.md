# Installing SIA

SIA can be installed as a Python CLI, vendored into one project, or both. The
CLI is the durable control plane; a vendored copy additionally lets the host
read the full guides directly.

## 1. Copy the package

Install the published package globally or in a virtual environment:

```powershell
python -m pip install sia-package
```

For development from a checkout:

```powershell
python -m pip install /path/to/SIA_package
```

Or vendor it in the target project:

```powershell
git clone https://github.com/GunjanGrunge/SIA_package.git C:\path\to\project\sia
python -m pip install C:\path\to\project\sia
```

The vendored directory must be named `sia/` because guide references use that
path. Initialize from the target project root:

```powershell
sia init --mode orchestrator
sia next --json
```

Use `advisory` if BMAD/Superpowers owns planning and execution, or `planning`
if another framework owns execution.

## 2. Gitignore the vendored package, keep the generated artifacts

If vendored, add exactly:

```gitignore
# Vendored SIA tooling
sia/
```

Do not ignore `.sia/`, the project's own skill, `AGENT.md`/`AGENTS.md`,
`docs/specs/`, `docs/plans/`, `logs/sessions/`, `skills/`, or `sdd/`. They are
auditable project history, like `_bmad-output`, and should normally be
committed. Review `.sia/events.jsonl` before committing because capture context
must not contain secrets.

## 3. Give your host a way to find `sia/AGENT.md`

Adapters are explicit opt-in launchers. Install one or more; they coexist:

```powershell
sia adapter install --host claude
sia adapter install --host codex
sia adapter install --host kiro
sia adapter install --host antigravity
```

They create only these namespaced files:

- Claude Code: `.claude/skills/sia/SKILL.md`
  (source: `integrations/claude-code/SKILL.md`)
- Codex: `.agents/skills/sia/SKILL.md`
- Kiro: `.kiro/steering/sia.md`
- Antigravity: `.agents/workflows/sia.md`

The Claude and Kiro launchers are manual-only. Every launcher runs
`sia next --json`, reads `sia/AGENT.md` when vendored (or `sia guide` when
installed alone), and resumes the persisted stage. No launcher installs an
always-on hook or replaces root instructions. Existing adapter paths are never
overwritten.

After Intake and project instruction authoring, generate the project's own
skill and `sdd/skill-manifest.md` as described in
`guides/writing-project-skills.md`.

## 4. Use native subagents

In orchestrator mode, prepare each task, invoke the host's own agent mechanism,
and record its real identity:

```powershell
sia task prepare --task api --brief sdd/api-brief.md --files src/api.py
sia task dispatch --task api --host kiro --agent-id backend --native-run-id <run-id>
sia task finish --task api --report sdd/api-report.md --review sdd/api-review.md `
  --reviewer-agent-id reviewer --review-native-run-id <review-run-id>
sia integration --evidence sdd/integration.md
sia advance
```

Disjoint task file sets may run in parallel. SIA serializes state updates and
rejects exact-path and parent/child ownership overlap. The controller must not
edit a dispatched task's owned files. Agent/run IDs are caller-attested records,
not cryptographically authenticated vendor receipts. SIA does not claim a
universal vendor agent API; if native subagents are unavailable, use
planning/advisory mode or an explicit manual handoff.

## 5. Check installation

```powershell
sia doctor
sia status
sia next --json
```

See `HOST-INTEGRATION.md` for stage ownership and plugin coexistence.

## 6. Attribution And Complete Usage

Public SIA-mediated work follows `guides/attribution.md`: retain the human Git
author, add the compact README attribution, and use `Assisted-by: SIA` plus an
`SIA-Run:` evidence path on future mediated commits. A direct user instruction
to omit attribution overrides this default. See `USAGE.md` for new-project,
existing-project, host-specific, modular-skill, and troubleshooting workflows.
