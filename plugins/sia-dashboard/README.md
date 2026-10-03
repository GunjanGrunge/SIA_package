# SIA dashboard

A live view of what SIA is doing in your project, inside Claude Code. It's a
[Claude Code mod](https://code.claude.com/docs/en/plugins/mods/overview) and
needs Claude Code 2.1.287 or later. Install it next to the `sia` plugin:

```text
/plugin install sia-dashboard@sia
```

## What it shows

A line above the prompt, in SIA projects only:

```text
SIA plan · 1 agent running · ~$0.176 saved · 3 skills · 1 rule   /sia-dashboard
```

`/sia-dashboard` opens a pane with four tabs:

| Tab | Shows |
|---|---|
| Overview | Agents running and seen this session, tokens handled by subagents, the estimated saving, session cost, skills, rules, and plan progress |
| Agents | The main conversation and every subagent, with its status, the model it ran on, and its tokens |
| Skills | The skills SIA wrote from your requirements, with uses this session and in total, plus other skills used |
| Calls | Every SIA tool with what it does. Press Enter on one to start a prompt that uses it |

Turn the line above the prompt off or on with `/sia-dashboard band off` and
`/sia-dashboard band on`.

## Where the numbers come from

- **Tokens** are measured. Every model request reports its token usage to the
  mod, tagged with the agent that made it.
- **Saved** is an estimate: each subagent request priced at your main model's
  rates, minus its price on the cheaper model it actually ran on. It assumes the
  main model would have used the same number of tokens. Prices come from the
  tier prices in SIA's orchestration config when set, otherwise from Anthropic's
  list prices. A model with no known price is named and left out.
- **Session** cost is Claude Code's own total, the same figure as `/cost`.
- **Skills** and **rules** are read from `.sia/` and refreshed every 1.5
  seconds. Skill use counts every Skill tool call, including calls inside
  subagents, and keeps a per-project total.

## Develop

```bash
claude plugin validate plugins/sia-dashboard
cd plugins/sia-dashboard && claude plugin test
claude --plugin-dir plugins/sia-dashboard   # hot-reloads on save
```
