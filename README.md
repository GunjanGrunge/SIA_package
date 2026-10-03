<p align="center">
  <img src="extension/icon.svg" alt="SIA logo" width="96" />
</p>

<h1 align="center">SIA</h1>

<p align="center">
  Self-Improving Agents: a workflow, memory and orchestration layer for AI coding assistants.<br>
  Works in Claude Code, Codex, Gemini CLI, Kiro and Antigravity.
</p>

<p align="center">
  <a href="https://gunjangrunge.github.io/SIA_package/">User guide</a> ·
  <a href="./CHANGELOG.md">Changelog</a> ·
  <a href="./LICENSE">MIT license</a> ·
  version 0.7.0
</p>

---

## What SIA does

- **Keeps the project on a plan.** Work moves through fixed stages, from intake
  to execution, and each stage needs a real file as evidence before SIA moves
  on. State lives in `.sia/`, so a new chat picks up where the last one stopped.
- **Learns from your corrections.** Tell the agent once ("keep replies short",
  "never touch `infra/`") and it becomes a standing rule for the project,
  recalled in every session and checked where a machine can check it.
- **Writes skills for your project.** SIA reads your spec and writes one skill
  per capability it calls for. Each skill quotes the requirement it serves, so
  nothing is invented.
- **Spends less on routine work.** Tasks are routed to cheap, normal or strong
  models by risk, with hard budget limits.
- **Keeps every subagent in line.** Each subagent starts with your rules and the
  project's skills, and every task is reviewed by a different agent.
- **Works with what you already use.** Superpowers, BMAD and other plugins keep
  working. SIA builds on them instead of replacing them.

## Install

SIA is a plugin. There is no `pip install`: the plugin bundles SIA and your host
starts it for you. The only prerequisite is Python 3.10 or newer, available as
`python3`.

| Host | Install |
|---|---|
| Claude Code | `/plugin marketplace add GunjanGrunge/SIA_package`<br>`/plugin install sia@sia` |
| Codex | `codex plugin marketplace add GunjanGrunge/SIA_package`<br>`codex plugin add sia@sia`<br>Older Codex (e.g. 0.121): `codex marketplace add GunjanGrunge/SIA_package`, then install **sia** from `/plugins` |
| Gemini CLI | `gemini extensions install https://github.com/GunjanGrunge/SIA_package` |
| Kiro | Powers panel → **Add Custom Power** → **Import power from GitHub** → paste `https://github.com/GunjanGrunge/SIA_package` → **Install** |
| Antigravity | `agy plugin install <path-to-a-clone>` |

Then, in your project, say **"set up SIA on this project"**.

<details>
<summary>Notes for Codex and Windows</summary>

**Codex asks before SIA writes.** Read-only tools run without a prompt; tools
that change `.sia/` ask for approval. In a non-interactive `codex exec` run,
allow SIA's own tools (and only those) with:

```text
-c 'plugins."sia@sia".mcp_servers.sia.default_tools_approval_mode="approve"'
```

**Windows** hosts launch `python3`. If only `python` or `py` is on your `PATH`,
SIA cannot start. Check with `python3 --version`; the Microsoft Store build of
Python provides it.

</details>

## Update

Pull the latest SIA into a host that already has it:

| Host | Update |
|---|---|
| Claude Code | `claude plugin marketplace update sia`<br>`claude plugin update sia@sia`<br>Or inside a session: `/plugin marketplace update sia`, then update **sia** from `/plugin` |
| Codex | `codex plugin marketplace upgrade sia`<br>`codex plugin add sia@sia` (reinstalls over the old copy)<br>Older Codex (e.g. 0.121): reinstall **sia** from `/plugins` |
| Gemini CLI | `gemini extensions update sia` (or `--all`) |
| Kiro | Powers panel → select **sia** → **Check for updates** → **Install updates** |
| Antigravity | `git pull` in your clone, then run `agy plugin install <path-to-the-clone>` again |

Then **restart the host**: Claude Code, Codex and Gemini CLI load the new version
only in a new session.

<details>
<summary>Notes on updating</summary>

**Installed from a local folder instead of GitHub?** `marketplace update` and
`marketplace upgrade` refresh GitHub sources only. Run `git pull` in that folder,
then the install or update command above. To switch to GitHub, remove the local
marketplace and add `GunjanGrunge/SIA_package` again.

**The dashboard is a separate plugin.** If you installed SIA before the
dashboard existed, add it once with `/plugin install sia-dashboard@sia`, then
update both plugins the same way.

**Nothing to update?** Hosts compare version numbers, so an update arrives only
when a release raises the version in the plugin manifests. Your project's
`.sia/` state, rules and skills stay where they are.

</details>

## How it works

### 1. A workflow with gates

```text
intake → spec → project-instructions → skills → plan → execution → feedback
```

At each stage the agent asks SIA what is required (`sia_next`), does the work,
and advances with the resulting file as evidence. A claim in conversation is
never evidence. If the agent tries to skip ahead, SIA refuses and says which
stage the project is at and what to do next.

Pick a mode when you start:

| Mode | SIA owns |
|---|---|
| `advisory` | Rules and feedback only. Another framework runs delivery. |
| `planning` | Intake through plan. Someone else executes. |
| `orchestrator` | Everything, including subagent dispatch, review and integration. |

### 2. Learning from corrections

Any correction or lasting preference becomes a rule, kept with your exact words
as evidence and scoped to the whole project or a folder.

- **Recall:** rules load at the start of every session and after `/compact`.
- **Enforcement:** rules a machine can check, such as a banned word, are checked
  on every file the agent writes and every reply. Violations go back to the
  agent to fix.
- **Subagents:** every subagent receives the rules when it starts, whoever
  spawned it.

Say a rule no longer applies and the agent retires it.

### 3. Skills written for your project

At the `skills` stage SIA reads the spec, plan and agent instructions, and
writes one skill per capability they ask for. Skills go where hosts find them:
`.claude/skills/` for Claude Code and `.agents/skills/` for Codex.

- Every skill quotes, word for word, the requirement it serves. SIA refuses one
  it cannot trace.
- Skills point to installed frameworks (for example Superpowers' test-driven
  development) instead of repeating them.
- New rules are written into the matching skills automatically.
- SIA never overwrites a skill it didn't write, and stops updating one you've
  edited.

### 4. Subagents and cost

In orchestrator mode SIA turns the plan into tasks that each own an exact set of
files, so parallel subagents cannot overwrite each other's changes.

| Tier | Used for | Claude Code default |
|---|---|---|
| cheap | low-risk, simple work | `haiku` |
| current | normal work and review | `sonnet` |
| strong | high-risk or complex work | `opus` |

Budgets are hard limits: going over stops the run. Each task is reviewed by a
different agent, and the run completes only after the combined changes pass
integration. Receipts record the model requested, the model used and token
usage, labelled as estimated when the host does not report it.

### 5. Working with other frameworks

SIA detects Superpowers and BMAD, whether copied into the repo or installed as
plugins. With Superpowers installed, its skills write the spec and plan, SIA is
the only dispatcher, and SIA's subagents use its test-driven development,
debugging and verification skills. You can also hand a whole stage to another
framework with `sia owner --stage plan --to bmad`.

### 6. A live dashboard (Claude Code)

Install `sia-dashboard` from the same marketplace to see SIA at work:

```text
/plugin install sia-dashboard@sia
```

A line above the prompt shows the stage, agents running, the estimated saving,
skills and rules. `/sia-dashboard` opens a pane with tabs for an overview, every
agent and the model it ran on, the skills SIA wrote and how often they're used,
and every SIA call. Token figures are measured from each model request; the
saving is an estimate against your main model's prices.
[Details](./plugins/sia-dashboard/README.md).

## What you can ask SIA to do

Your assistant calls these for you. You can also ask for one by name ("run
`sia_next`"), or pick one from the dashboard's Calls tab.

| Area | Call | What it does |
|---|---|---|
| Workflow | `sia_init` | Set up SIA in a project |
| | `sia_status` | Where the project is: mode, stage, tasks |
| | `sia_next` | What the current stage needs and how to advance |
| | `sia_advance` | Complete the current stage, citing a file as evidence |
| | `sia_owner` | Hand a stage to another framework, such as BMAD |
| | `sia_doctor` | Check the setup and list other frameworks found |
| | `sia_guide` | Print SIA's full workflow contract |
| Learning | `sia_rule_learn` | Turn a correction or preference into a standing rule |
| | `sia_rule_list` | List the active rules |
| | `sia_rule_retire` | Retire a rule that no longer applies |
| | `sia_preflight` | Load the rules that apply to files about to change |
| | `sia_record`, `sia_capture` | Record an outcome or a deviation |
| | `sia_convergence` | Deviation rate per error class, to see the loop working |
| Project skills | `sia_skill_context` | Requirements, dependencies and existing skills, before writing |
| | `sia_skill_write` | Write one requirement-backed skill |
| | `sia_skill_list` | List the skills SIA wrote and what each serves |
| | `sia_skill_retire` | Remove a skill the project no longer needs |
| Orchestration | `sia_orchestrate_example` | A config template for model tiers and budgets |
| | `sia_orchestrate_configure` | Store model tiers, prices and budget limits |
| | `sia_task_prepare` | Define one task and the exact files it owns |
| | `sia_orchestrate_plan` | Route tasks to tiers and reserve the budget |
| | `sia_orchestrate_receipt` | Record a subagent's result |
| | `sia_orchestrate_status` | Progress, budget use and telemetry quality |
| | `sia_integration` | Record validation of the combined changes |

## What has been verified

| | Claude Code | Codex | Kiro | Gemini / Antigravity |
|---|---|---|---|---|
| Install and tools | ✅ | ✅ | ✅ installs | not tested |
| Rules: learn, recall, enforce | ✅ | hooks not tested | not tested | not tested |
| Rules and skills reach subagents | ✅ | not tested | not tested | not tested |
| Project skills | ✅ | written, not tested live | not yet | not yet |
| Model routing | ✅ Haiku / Sonnet | not tested | not tested | not tested |
| Live dashboard | ✅ | not available | not available | not available |

Results from live Claude Code runs:

- **Rules:** with a "no em dashes" rule, a new session answered with none. The
  same question without the rule produced 15.
- **Project skills:** a churn-model spec with fixed hyperparameters produced
  data-profiling, training and evaluation skills, and no tuning skill, even
  though `optuna` was installed.
- **Orchestration:** the implementer ran on Haiku and the reviewer on Sonnet as
  routed, both received the rules, and the run passed integration.

On very small tasks the main session's own planning costs more than delegation
saves (about $1 per test run). The saving grows with the amount of work handed
out.

## Reference

<details>
<summary>CLI commands</summary>

The plugin exposes these as tools. The CLI is useful for scripting.

```text
sia init --mode advisory|planning|orchestrator
sia next --json                   what the current stage requires
sia advance --evidence <path>     complete the current stage
sia status | sia doctor

sia rule learn --text ... --user-quote ...   turn a correction into a rule
sia rule list | sia rule retire --id ...
sia preflight --scope <path>      rules that apply before touching files

sia skill context                 requirements, dependencies, existing skills
sia skill write --file skill.json write a requirement-backed skill
sia skill list | sia skill retire --name ...

sia task prepare ...              task brief, owned files, risk, estimate
sia orchestrate configure ...     models, prices, budgets
sia orchestrate plan ...          route tasks and reserve budget
sia orchestrate receipt ...       record a subagent's result
sia orchestrate status            progress, budget, telemetry
sia integration --evidence ...    validate the combined changes

sia owner --stage <stage> --to <framework>
```

</details>

<details>
<summary>Files SIA writes</summary>

```text
.sia/
├── config.json      mode, models, budgets, stage owners
├── state.json       current stage, tasks, history
├── events.jsonl     corrections and outcomes
├── rules.json       active and retired rules
├── skills.json      generated project skills
└── runs/<run-id>/   dispatch plans, receipts, integration

.claude/skills/<name>/SKILL.md   project skills for Claude Code
.agents/skills/<name>/SKILL.md   project skills for Codex
sdd/skill-manifest.md            which requirement each skill serves
```

`.sia/` can contain your corrections and review notes. Check it for secrets
before committing.

</details>

<details>
<summary>Running the CLI without a host</summary>

Only needed for scripting, or for the `standalone` backend, where SIA launches
provider CLIs you configure. Those run as argument arrays with `shell=False`
behind an explicit `sia orchestrate run --approve-commands` gate that agents
cannot trigger.

```bash
python -m pip install "git+https://github.com/GunjanGrunge/SIA_package"
sia init --mode orchestrator
```

Install from GitHub: the `sia-package` release on PyPI is an old 0.2.0 without
orchestration. See [INSTALL.md](./INSTALL.md) for vendoring SIA into a repo.

</details>

## More

- [User guide](https://gunjangrunge.github.io/SIA_package/): the full walkthrough
- [USAGE.md](./USAGE.md): hosts, existing projects, attribution
- [HOST-INTEGRATION.md](./HOST-INTEGRATION.md): modes and the host contract
- [VALIDATION.md](./VALIDATION.md): how SIA is tested
- [Issues](https://github.com/GunjanGrunge/SIA_package/issues)

## License

MIT
