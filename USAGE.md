# Using SIA

> **Interactive documentation:** [Complete SIA User Guide](https://gunjangrunge.github.io/SIA_package/) — including Claude Code, Codex, Gemini CLI, Antigravity, and Kiro setup.

SIA is a project-adaptive guidance layer for a coding assistant. It does
not replace Claude Code, Codex, or another host: the host supplies the
model, terminal, Git, and native subagents; SIA supplies the workflow,
project memory, generated skills, evidence requirements, and human
approval gates.

You install SIA once per project. After that, you state what you want to
build; you do not need to create skills, task briefs, or a process plan
yourself.

## Quick Start

Install the persistent runtime, initialize an explicit mode, and install only
the host adapter you want:

```bash
python -m pip install sia-package==0.2.0
sia init --mode orchestrator
sia adapter install --host claude
sia next --json
```

Vendoring the repository as `sia/` remains supported. In that case, ask the
host to read `sia/AGENT.md`; the persisted `.sia/` packet remains authoritative
for the current stage.

## What SIA Does For You

After you state a goal, SIA should:

1. identify whether the project is new, existing software, a document, or
   a design task;
2. preserve any existing project instructions or framework folders;
3. generate a project `AGENT.md`, a spec, and a plan from your project;
4. generate the smallest useful project skill pack and record it in
   `sdd/skill-manifest.md`;
5. use the host's native subagents for implementation tasks when they are
   available;
6. retain the task brief, dispatch, report, review, usage, and integration
   evidence; and
7. capture verified mistakes as project-specific standing rules so they
   are checked before related future work.

The host harness executes the work. SIA coordinates the process around it.

## SIA Attribution

Public SIA projects use both forms of attribution automatically: a compact
README badge and evidence trailers on future SIA-mediated commits. No command
or toggle is required. Trailers retain the existing human Git author and link
to the relevant SIA evidence record. A direct user instruction to omit
attribution is respected and recorded. The full policy and exact formats are
in [`guides/attribution.md`](./guides/attribution.md).

## New Project

For an empty or early-stage project, create or open the project directory,
install SIA, and use the Quick Start message above. Then describe the
outcome in plain language, for example:

```text
I want to build a small Python CLI that helps a team compare two CSV files.
It must run offline and have tests. Ask me only the decisions that matter
before writing code.
```

SIA will classify the work as greenfield software, ask about unresolved
requirements and risk, write the project artifacts, synthesize the
project operating skill, and present a plan for approval. Do not ask it to
skip directly to implementation if you want the full SIA workflow.

Before implementation, expect artifacts similar to:

```text
AGENT.md
docs/specs/<date>-<project>-design.md
docs/plans/<date>-<project>-plan.md
skills/<project>-sia/SKILL.md
sdd/skill-manifest.md
```

Once you approve the plan, SIA uses the host's own subagent mechanism. It
does not create a separate model account, runner, or cloud service.

## Existing Project

SIA is deliberately cautious with an existing repository. Install it at
the repository root, then begin with a concrete request such as:

```text
Read `sia/AGENT.md` in full and follow it. This is an existing application.
I want to add account export. First inspect the current architecture and
existing instructions; do not modify anything until you show me the plan.
```

For an existing project, SIA should first locate the README, current
instruction files, specs, tests, and relevant source files. Existing
`AGENT.md`, `AGENTS.md`, `CLAUDE.md`, `.cursor/`, or other agent-framework
files remain in place. SIA records their boundaries in the generated
project contract; it does not delete, rewrite, or replace them.

If you only want feedback or diagnosis, say so clearly:

```text
Read `sia/AGENT.md` and review this authentication flow. Do not edit files.
Give me findings, risks, and the smallest safe implementation plan.
```

## Claude Code

The Quick Start message always works. For automatic discovery in later
Claude Code sessions, copy the supplied discovery shim from
`sia/integrations/claude-code/SKILL.md` to
`.claude/skills/sia/SKILL.md` in the target project.

The shim is only a launcher. SIA later generates the project-specific
Claude Code skill at:

```text
.claude/skills/<project-slug>-sia/SKILL.md
```

That generated skill derives its rules from the project's goal, approved
spec, plan, and active feedback rules. It still defers to user
instructions and the project `AGENT.md`.

## Codex

Use the same Quick Start message at the start of the Codex task:

```text
Read `sia/AGENT.md` in full and follow it.
```

SIA then uses the Codex harness already available in that session for
terminal work, Git, tests, and scoped collaboration. The host-neutral
source skill remains in `skills/<project>-sia/SKILL.md`; SIA reads it as
project context even when a host uses a different discovery convention.

Keep existing `AGENTS.md` instructions. SIA's generated project
`AGENT.md` records how those instructions interact instead of silently
overwriting them.

## Collaborating with Native Skills & Plugins (`BMAD`, `Superpowers`, MCP)

If your project already uses native skill packs or plugins such as `BMAD` (`_bmad/` or `.claude/skills/bmad-*`), `Superpowers`, `.cursor/rules/`, or MCP tools:

1. **Coexistence**: SIA detects existing skills/plugins during Intake and records them in the project `AGENT.md`. SIA never overwrites or deletes native plugin files.
2. **Reading Native Context**: SIA reads discovered native skills as domain authority and tool capability providers.
3. **Multi-Agent Spawning & Delegation**: When SIA breaks work into tasks and dispatches subagents, it injects relevant native skill context into each subagent's task brief. Subagents execute using native tools/skills (e.g. running `/bmad` workflows or `/superpowers` tools).
4. **Process Refinement**: SIA's feedback loop (`capture-interface.md`) monitors subagent results, captures any process failures or corrections, and refines future task briefing so multi-agent execution improves over time.

## During Implementation

When the approved plan is ready, a compliant SIA run leaves an auditable
trail in `sdd/`:

```text
sdd/skill-manifest.md
sdd/task-N-brief.md
sdd/task-N-dispatch.md
sdd/task-N-report.md
sdd/progress.md
```

For normal implementation tasks, the controller briefs and reviews while
the host's scoped subagents write the task-owned files. Each task carries
an effort budget. If the host cannot spawn subagents or cannot provide
dispatch evidence, SIA must say that execution is blocked rather than
pretending direct controller work was delegated.

Useful follow-up messages include:

```text
Show me the approved plan and the risk level of each action.
Execute the approved plan using scoped subagents and keep the SIA evidence trail.
Pause after the next high-severity decision and ask me first.
Summarize the current progress, tests, subagent reports, and token usage.
Run integration and show me the final report; do not call the work complete until then.
```

## Files To Commit

Ignore the vendored `sia/` directory in the target project's `.gitignore`.
Commit the artifacts SIA creates for your project instead:

```text
AGENT.md
docs/specs/
docs/plans/
skills/
logs/sessions/
sdd/
```

Never put secrets, `.env` contents, keys, or tokens into generated skills,
task reports, plans, or session logs.

## Updating SIA

If the package was cloned with Git, update the vendored package from the
target project root with:

```bash
git -C sia pull
```

Review SIA release notes before resuming a plan. Existing project
artifacts remain yours; an update should not replace them. SIA should
record any material generated-skill change in `sdd/skill-manifest.md`.

## Checking Backend Status And Usage

Use the persistent backend rather than the cosmetic banner:

```bash
sia status
sia next --json
sia convergence
```

These commands report the runtime mode, current stage and owner, task states,
integration evidence, and recorded feedback. Token/cost values are shown only
when host telemetry exists; otherwise usage and savings must be labeled as
estimates.

## Invoking SIA Mid-Project (Brownfield)

If you have an existing project already in development and want to invoke SIA mid-way:

1. Clone or copy SIA into `sia/` at your project root.
2. Send this instruction to your assistant:
   ```text
   Read `sia/AGENT.md` in full and follow it. This is an existing ongoing project.
   I want to initialize SIA mid-project to help me add [Feature Name].
   Mode: Brownfield Intake. Inspect existing code and instructions without modifying them.
   ```
3. SIA will perform a safe Intake check, identify existing architecture and instructions, derive modular feature skills, and present an implementation plan before writing any code.

## Modular Feature Skills & Multi-Engine Collaboration

SIA does not dump your project into one giant monolithic skill file. Instead, it analyzes your project architecture and generates a **Modular Skill Pack** containing focused, feature-specific skills (e.g. `skills/<project>-theme-manager/SKILL.md`, `skills/<project>-product-search/SKILL.md`).

Because these skill files are saved in standard host-neutral formats (`skills/`) and discoverable host paths (`.claude/skills/`, `.agents/skills/`), different AI coding assistants (Claude Code, Codex, Antigravity IDE, Cursor) can collaborate seamlessly on the exact same project using the same feature-specific skill rules.

## Working Directory Execution Safety

All SIA subagent tasks, commands (`python main.py`, `npm test`), and generated files MUST run in your **Project Root Directory**. SIA explicitly prevents execution inside hidden sandbox folders like `.claude/workingtree/` so your project files stay cleanly organized in your workspace.

## Troubleshooting

- **No banner appeared:** the host may have hidden shell output. This is
  cosmetic; the workflow starts when `sia/AGENT.md` is read.
- **Project files running in `.claude/workingtree`:** stop the task and use
  `sia status` to confirm the intended project root before redispatching.
  Working-directory safety is enforced by task ownership and host policy, not
  by the cosmetic banner.
- **No usage estimate shown:** run `sia convergence` for persisted feedback
  metrics. Token/cost savings require host telemetry or must be labeled as
  estimates.
- **No subagents were used:** inspect `sdd/`. Missing dispatch and report
  artifacts mean the run is not compliant with the execution gate.
- **SIA conflicts with existing instructions:** user instructions win,
  followed by the project's own instructions. Ask SIA to record the
  boundary rather than deleting either system.
- **You want a smaller process:** say so. SIA can scope the plan down, but
  it should still preserve approvals, verification, and honest reporting.
