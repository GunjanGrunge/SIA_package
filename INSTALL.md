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
sia adapter install --host gemini
sia adapter install --host antigravity
```

They create only these namespaced files:

- Claude Code: `.claude/skills/sia/SKILL.md`
  (source: `integrations/claude-code/SKILL.md`)
- Codex: `.agents/skills/sia/SKILL.md`
- Kiro: `.kiro/steering/sia.md`
- Gemini CLI: `.gemini/skills/sia/SKILL.md`
- Antigravity: `.agents/workflows/sia.md`

The Claude and Kiro launchers are manual-only. Every launcher runs
`sia next --json`, reads `sia/AGENT.md` when vendored (or `sia guide` when
installed alone), and resumes the persisted stage. No launcher installs an
always-on hook or replaces root instructions. Existing adapter paths are never
overwritten.

After Intake and project instruction authoring, generate the project's own
skill and `sdd/skill-manifest.md` as described in
`guides/writing-project-skills.md`.

## 4. Configure And Run Cost-Aware Subagents

Generate a config template and set exact cheap/current/strong model IDs,
configured prices, hard budgets, concurrency, and optional standalone workers:

```powershell
sia orchestrate example > orchestration.json
sia orchestrate configure --file orchestration.json
```

Prepare bounded tasks, then choose a backend:

```powershell
sia task prepare --task api --brief sdd/api-brief.md --files src/api.py `
  --risk high --complexity complex --estimated-tokens 40000

# Active assistant launches native workers and submits receipts.
sia orchestrate plan --backend native-host --host kiro
sia orchestrate receipt --file api-implement-receipt.json

# Or SIA launches approved provider CLI command arrays itself.
sia orchestrate plan --backend standalone --host provider-cli
sia orchestrate run --approve-commands

sia orchestrate status
sia integration --evidence sdd/integration.md
sia advance
```

Disjoint implementers run in parallel; reviewers unlock after implementer
receipts. SIA rejects ownership overlap, hard-budget plans, model mismatch,
invalid receipts, duplicate reviewer identity, and unfinished integration.
Native IDs remain caller-attested. Standalone processes are observed and
shell-free but are not an OS sandbox. See `guides/orchestration.md`.

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
