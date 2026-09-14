<p align="center">
  <img src="./assets/sia-banner.png" alt="SIA: Self-Improving Agents" width="100%" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0--alpha-00F2FE.svg?style=flat-square" alt="Version 0.1.0-alpha" />
  <img src="https://img.shields.io/badge/status-active-success.svg?style=flat-square" alt="Status: Active" />
  <img src="https://img.shields.io/badge/license-MIT-lightgrey.svg?style=flat-square" alt="License: MIT" />
  <img src="https://img.shields.io/badge/host--agnostic-yes-7B2CBF.svg?style=flat-square" alt="Host-agnostic" />
</p>

<p align="center">
  <img src="./assets/sia-mark.svg" alt="SIA mark" width="48" />
</p>

<p align="center">
  <b>A portable, host-agnostic instruction package that turns a coding
  assistant into a self-improving project collaborator.</b>
</p>

It generates fresh, project-specific process artifacts: an `AGENT.md`, a
spec, a plan, **host-discoverable project skills**, and auditable
subagent task records. You install SIA and state the goal; SIA derives
the needed skills, delegates implementation through the host harness,
reviews the results, and reports the integrated outcome.

This repo **is** the package. Clone it directly into a project as
`sia/` and you're set up.

## Architecture

<p align="center">
  <img src="./assets/architecture-flowchart.png" alt="SIA full pipeline diagram: Entry Point, Intake &amp; Classification, Planning &amp; Approval, Execution Layer, Validation &amp; Delivery, Learning &amp; Continuous Improvement" width="100%" />
</p>

The full six-stage pipeline this package implements — see `AGENT.md` for
the authoritative step-by-step version this diagram summarizes.

## Install

```bash
git clone https://github.com/GunjanGrunge/SIA_package.git /path/to/your-project/sia
```

Then, in `your-project/`:

1. **Read [`sia/INSTALL.md`](./INSTALL.md)** — gitignoring this vendored
   folder correctly (while keeping the artifacts SIA *generates* for
   your project committed), and an optional Claude Code discovery shim.
2. **Tell your assistant once:** *"Read `sia/AGENT.md` and follow it."*
   That's the one mandatory entry point — from there it runs Intake,
   asks what it needs to, and generates your project's own `AGENT.md`,
   spec, project skill(s), and plan using the guides under `sia/guides/`.
   During execution it requires a brief, dispatch record, subagent report,
   reviewer verdict, and integration report for each planned task.

No API keys, no account, no cloud dependency. It's plain markdown
instructions plus a small Python structure-test harness
(`tests/validate_sia.py`) used only when developing this package itself.

For the complete new-project, existing-project, Claude Code, Codex,
subagent, reporting, and update workflow, read [USAGE.md](./USAGE.md).

### Existing project? You choose the starting mode

After the minimal safety check, SIA asks which way you want to begin:

1. **Repository-informed exploration** — SIA reads a bounded set of
   relevant artifacts, explains what it knows and does not know, then
   asks what you want to build or change.
2. **Goal-first** — SIA skips the broad repository scan and asks what you
   want immediately, reading only what is needed for that request.
3. **Conversational discovery** — you describe the project first; SIA
   verifies only the evidence needed for the work that emerges.

The chosen mode, evidence read, knowns, unknowns, and goal become part of
the generated project record. SIA never claims it understands files it
has not examined.

### Attribution is automatic

The public distribution adds a compact README badge and trailers to future
SIA-mediated commits automatically—no slash command or toggle required.
Trailers credit SIA's workflow while keeping the existing human Git author
intact and linking the commit to project evidence. A direct user instruction
to omit attribution is respected. See
[`guides/attribution.md`](./guides/attribution.md) for the exact policy.

## What's in here

```
AGENT.md                          # bootstrap — read this first
guides/
├── questioning-and-approval.md   # batching questions, severity-tagged approval gates
├── writing-agent-md.md           # how to author a project's own AGENT.md
├── writing-spec.md               # how to author a project spec
├── writing-plan.md               # how to break a spec into a plan (file ownership, integration phase)
├── writing-project-skills.md     # how SIA derives host-discoverable project skills
├── subagent-task-brief.md        # task brief / report / progress-log / integration-report formats
└── security-gate.md              # fixed threat-class checklist (software projects only)
capture-interface.md              # feedback capture + the self-healing loop-engineering mechanism
integrations/claude-code/SKILL.md # optional Claude Code auto-discovery shim
INSTALL.md                        # how to add this to a project (gitignore policy, discovery)
VALIDATION.md                     # the dogfood checklist this package is tested against
USAGE.md                          # complete user guide for new and existing projects
CHANGELOG.md
tests/                            # structure-test harness (dev tooling, not needed to use SIA)
```

## Core idea

SIA is a *generator*, not a library of pre-built templates. Every
project gets its own fresh `AGENT.md`, spec, plan, and skill pack — never copied
from another project — authored using the guides here. The one
exception is `guides/security-gate.md`, a fixed, reused checklist for
software projects.

When a host supports subagents, SIA's controller is not allowed to
silently replace a delegated implementation task with direct coding. A
task is complete only with durable dispatch, implementation, review, and
integration evidence; otherwise SIA reports the execution limitation to
the user.

The feedback loop (`capture-interface.md`) turns verified mistakes into
project-specific standing rules with full provenance (source, evidence,
severity, error class, scope, date, active/retired status), re-checked
before every future proposal — so a project accumulates fewer repeated
mistakes over its life instead of a longer history of the same ones.

## Validation

`VALIDATION.md` is the dogfood checklist this package is tested against
before a version is called stable — real, previously-unseen codebases,
not synthetic examples. A pilot validation report covering several real
runs (including a full multi-subagent execution path: scoped task
briefs, independent implementer subagents, an independent reviewer, and
a real integration build) is maintained separately; ask the maintainer
for a link if you want to see it.

## License

MIT.
