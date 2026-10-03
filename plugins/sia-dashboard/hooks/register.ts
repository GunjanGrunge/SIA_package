// SIA dashboard: a live pane (/sia-dashboard) and a one-line band above the
// prompt showing what SIA is doing in this project: agents at work, tokens
// handled by subagents and the estimated saving from cheaper models, the
// skills SIA wrote and how often they are used, and the calls SIA offers.
//
// Token figures are measured, not guessed: every model request reports its
// usage at `turn.step`, tagged with the agent loop that made it.

import {
  clip,
  fmtTokens,
  fmtUsd,
  isSiaTool,
  loopModels,
  loopTokens,
  record,
  savings,
  shortModel,
  shortTool,
  siaSnapshot,
  skillMatches,
  type Ledger,
  type SiaSnapshot,
} from './metrics.ts'

const PANE = 'sia-dashboard'
const TABS = [
  { id: 'overview', label: 'Overview', hotkey: '1' },
  { id: 'agents', label: 'Agents', hotkey: '2' },
  { id: 'skills', label: 'Skills', hotkey: '3' },
  { id: 'calls', label: 'Calls', hotkey: '4' },
] as const

type AgentRow = { id: string; type: string; description: string; status: string }

// Session state. A reload of this module (a save during development) starts
// these over; skill use counts are also kept per project in $.store.
let tab: (typeof TABS)[number]['id'] = 'overview'
let ledger: Ledger = {}
let agentModels: Record<string, string> = {}
// Every subagent seen this session. $.agent.list() drops an agent once it
// finishes, so the dashboard keeps its own record.
let agents: Record<string, AgentRow> = {}
let sia: SiaSnapshot | undefined
let mainModel = ''
let sessionUsd: number | undefined
let skillUses: Record<string, number> = {}
let projectUses: Record<string, number> = {}
let siaTools: { name: string; description: string }[] = []
let showBand = true

// --- helpers that take $ (top-level, so `claude plugin validate` can follow them)

function parentOf(dir: string): string | undefined {
  const trimmed = dir.replace(/[\\/]+$/, '')
  const at = Math.max(trimmed.lastIndexOf('/'), trimmed.lastIndexOf('\\'))
  if (at <= 0) return undefined
  const parent = trimmed.slice(0, at)
  return /^[A-Za-z]:$/.test(parent) ? parent + '\\' : parent
}

function join(dir: string, ...parts: string[]): string {
  const sep = dir.includes('\\') && !dir.includes('/') ? '\\' : '/'
  return [dir.replace(/[\\/]+$/, ''), ...parts].join(sep)
}

async function readOr($, path: string): Promise<string | undefined> {
  try {
    return await $.fs.read(path)
  } catch {
    return undefined
  }
}

/** The nearest directory at or above the working directory that holds .sia/state.json. */
async function findSiaRoot($): Promise<string | undefined> {
  let dir: string | undefined = await $.session.cwd()
  for (let depth = 0; dir && depth < 12; depth++) {
    if (await $.fs.exists(join(dir, '.sia', 'state.json'))) return dir
    dir = parentOf(dir)
  }
  return undefined
}

async function refreshSia($): Promise<void> {
  const root = await findSiaRoot($)
  if (!root) {
    sia = undefined
    return
  }
  sia = siaSnapshot(root, {
    config: await readOr($, join(root, '.sia', 'config.json')),
    state: await readOr($, join(root, '.sia', 'state.json')),
    rules: await readOr($, join(root, '.sia', 'rules.json')),
    skills: await readOr($, join(root, '.sia', 'skills.json')),
  })
  const stored = await $.store.get('uses:' + root)
  projectUses = stored && typeof stored === 'object' ? (stored as Record<string, number>) : {}
}

async function refreshAll($): Promise<void> {
  try {
    const list = await $.agent.list()
    const live = new Set(list.map((a) => a.id))
    for (const a of list) agents[a.id] = { id: a.id, type: a.type, description: a.description, status: a.status }
    // One that left the list while running has finished.
    for (const a of Object.values(agents)) if (!live.has(a.id) && a.status === 'running') a.status = 'completed'
  } catch {
    // Keep what was seen.
  }
  try {
    mainModel = await $.session.model()
    const usage = await $.session.usage()
    sessionUsd = usage.cost?.usd
  } catch {
    // Usage is unavailable on some hosts; the dashboard omits the line.
  }
  await refreshSia($)
}

async function countSkillUse($, called: string): Promise<void> {
  skillUses[called] = (skillUses[called] ?? 0) + 1
  const name = sia?.skills.find((s) => skillMatches(called, s.name))?.name
  if (!name || !sia) return
  // Read again right before writing: other sessions share the store.
  const key = 'uses:' + sia.root
  const stored = await $.store.get(key)
  const uses = stored && typeof stored === 'object' ? { ...(stored as Record<string, number>) } : {}
  uses[name] = (uses[name] ?? 0) + 1
  await $.store.set(key, uses)
  projectUses = uses
}

// --- figures shown on every tab and in the band ------------------------------

function usesOf(name: string): number {
  return Object.entries(skillUses)
    .filter(([called]) => skillMatches(called, name))
    .reduce((sum, [, count]) => sum + count, 0)
}

function agentRows(): AgentRow[] {
  // A subagent can report usage before it shows up in the list.
  for (const loop of Object.keys(ledger)) {
    if (loop !== 'main' && !agents[loop]) agents[loop] = { id: loop, type: 'subagent', description: loop, status: 'completed' }
  }
  return Object.values(agents)
}

function figures() {
  const rows = agentRows()
  const running = rows.filter((a) => a.status === 'running').length
  const saved = savings(ledger, mainModel, sia?.overrides ?? {})
  const siaSkills = (sia?.skills ?? []).filter((s) => s.status === 'active')
  const usesThisSession = siaSkills.reduce((sum, s) => sum + usesOf(s.name), 0)
  return { rows, running, saved, siaSkills, usesThisSession }
}

export function register(on) {
  on('session.start', async ($, e, next) => {
    const band = await $.store.get('band')
    showBand = band !== 'off'
    await refreshAll($)
    try {
      const tools = await $.tool.list()
      siaTools = tools.filter((t) => isSiaTool(t.name)).map((t) => ({ name: t.name, description: t.description }))
    } catch {
      siaTools = []
    }
    // Agents and SIA's files change outside any event this mod sees, so poll.
    $.clock.every(1500, async () => {
      await refreshAll($)
      $.ui.invalidate('ui.render')
    })
    await $.command.register({
      name: 'sia-dashboard',
      description: 'Open the SIA dashboard: agents, token savings, skills, and SIA calls',
      argumentHint: '[band on|off]',
      immediate: true,
    })
    return next(e)
  })

  // Every model request, main loop or subagent, reports its usage here.
  on('turn.step', async function* ($, e, next) {
    const result = yield* next(e)
    try {
      if (result?.usage) {
        record(ledger, e.agentId ?? 'main', result.usage.model || e.model, result.usage)
        $.ui.invalidate('ui.render')
      }
    } catch {
      // Never let bookkeeping break a turn.
    }
    return result
  })

  // The model each subagent actually started on.
  on('agent.spawn', async ($, e, next) => {
    const result = await next(e)
    if (result && result.agentId && result.model) {
      agentModels[result.agentId] = result.model
      agents[result.agentId] ??= { id: result.agentId, type: e.subagentType, description: e.description, status: 'running' }
      $.ui.invalidate('ui.render')
    }
    return result
  })

  // Skill use, in the main loop and inside subagents.
  on('tool.call', { tool: 'Skill' }, async ($, e, next) => {
    const called = typeof e.skill === 'string' ? e.skill : undefined
    if (called) {
      try {
        await countSkillUse($, called)
        $.ui.invalidate('ui.render')
      } catch {
        // Counting is best effort.
      }
    }
    return next(e)
  })

  on('command.run', { command: 'sia-dashboard' }, async ($, e) => {
    const arg = e.args.trim().toLowerCase()
    if (arg === 'band off' || arg === 'band on') {
      showBand = arg === 'band on'
      await $.store.set('band', showBand ? 'on' : 'off')
      $.ui.invalidate('ui.render')
      return { text: 'SIA band above the prompt is ' + (showBand ? 'on' : 'off') + '.' }
    }
    await refreshAll($)
    await $.ui.open({ id: PANE, title: 'SIA', focus: true, closeOnEscape: true })
    return {}
  })

  // The one-line band above the prompt, in SIA projects only.
  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (!showBand || !sia) return next(e)
    const { Box, Text } = $.ui.resolve(e)
    const f = figures()
    const parts = [
      sia.stage ? sia.stage : 'done',
      f.running + ' agent' + (f.running === 1 ? '' : 's') + ' running',
      f.saved.routedTokens > 0 ? '~' + fmtUsd(f.saved.saved) + ' saved' : fmtTokens(f.saved.subagentTokens) + ' subagent tokens',
      f.siaSkills.length + ' skill' + (f.siaSkills.length === 1 ? '' : 's'),
      sia.rules + ' rule' + (sia.rules === 1 ? '' : 's'),
    ]
    const line = Box({
      flexDirection: 'row',
      columnGap: 1,
      children: [
        Text({ bold: true, color: 'cyan', children: ['SIA'] }),
        Text({ dimColor: true, wrap: 'truncate-end', children: [parts.join(' · ') + '   /sia-dashboard'] }),
      ],
    })
    // Keep whatever other mods draw in the band.
    const theirs = await next(e)
    return theirs ? Box({ flexDirection: 'column', children: [theirs, line] }) : line
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== PANE) return next(e)
    const { Box, Text, Button } = $.ui.resolve(e)
    const width = Math.max(30, (e.props.bodyColumns ?? 60) - 2)
    const nameWidth = Math.max(12, Math.min(34, width - 24))
    const redraw = () => $.ui.invalidate('ui.render')
    const f = figures()

    const row = (label: string, value: string, note?: string) =>
      Box({
        key: 'row-' + label,
        flexDirection: 'row',
        children: [
          Text({ dimColor: true, children: [label.padEnd(11)] }),
          Text({ children: [value] }),
          ...(note ? [Text({ dimColor: true, wrap: 'truncate-end', children: ['  ' + note] })] : []),
        ],
      })

    const tabs = Box({
      flexDirection: 'row',
      columnGap: 3,
      children: TABS.map((t) =>
        Button({
          key: 'tab-' + t.id,
          label: t.label,
          hotkey: t.hotkey,
          plain: true,
          dimColor: tab !== t.id,
          onPress: () => {
            tab = t.id
            redraw()
          },
        }),
      ),
    })

    const header = Box({
      flexDirection: 'row',
      columnGap: 1,
      children: sia
        ? [
            Text({ bold: true, color: 'cyan', children: ['SIA'] }),
            Text({ children: [(sia.stage ?? 'workflow complete') + (sia.mode ? '  (' + sia.mode + ' mode)' : '')] }),
          ]
        : [
            Text({ bold: true, color: 'cyan', children: ['SIA'] }),
            Text({ dimColor: true, children: ['not set up here. Say "set up SIA on this project".'] }),
          ],
    })

    let body: any[] = []

    if (tab === 'overview') {
      const s = f.saved
      body = [
        row('Agents', f.running + ' running', f.rows.length + ' this session'),
        row('Subagents', fmtTokens(s.subagentTokens) + ' tokens', 'kept out of the main conversation'),
        s.routedTokens > 0
          ? row('Saved', '~' + fmtUsd(s.saved), 'estimate vs ' + shortModel(mainModel) + ': ' + fmtTokens(s.routedTokens) + ' tokens on cheaper models')
          : row('Saved', '-', 'no subagent has run on a cheaper model yet'),
        ...(sessionUsd !== undefined ? [row('Session', fmtUsd(sessionUsd), 'spent so far')] : []),
        row('Skills', f.siaSkills.length + ' written by SIA', f.usesThisSession + (f.usesThisSession === 1 ? ' use' : ' uses') + ' this session'),
        row('Rules', (sia?.rules ?? 0) + ' active', 'loaded into every session and subagent'),
        ...(sia?.operations
          ? [row('Plan', sia.operations.complete + '/' + sia.operations.total + ' operations done', sia.operations.status ?? '')]
          : []),
        ...(s.unpriced.length
          ? [Text({ key: 'unpriced', dimColor: true, children: ['No price known for ' + s.unpriced.map(shortModel).join(', ') + '; left out of the saving.'] })]
          : []),
      ]
    } else if (tab === 'agents') {
      const agentRow = (key: string, mark: string, color: string | undefined, name: string, model: string, tokens: number) =>
        Box({
          key,
          flexDirection: 'row',
          children: [
            Text({ ...(color ? { color } : { dimColor: true }), children: [mark + ' '] }),
            Text({ children: [clip(name, nameWidth).padEnd(nameWidth)] }),
            Text({ dimColor: true, children: ['  ' + (model ? shortModel(model) : '?').padEnd(11) + fmtTokens(tokens)] }),
          ],
        })
      body = [
        agentRow('agent-main', '●', 'cyan', 'main conversation', mainModel, loopTokens(ledger, 'main')),
        ...(f.rows.length === 0 ? [Text({ key: 'no-agents', dimColor: true, children: ['No subagents yet this session.'] })] : []),
        ...f.rows.map((a) =>
          agentRow(
            'agent-' + a.id,
            a.status === 'running' ? '●' : a.status === 'completed' ? '✓' : '✗',
            a.status === 'running' ? 'green' : a.status === 'completed' ? undefined : 'red',
            a.type + ': ' + a.description,
            agentModels[a.id] ?? loopModels(ledger, a.id)[0] ?? '',
            loopTokens(ledger, a.id),
          ),
        ),
      ]
    } else if (tab === 'skills') {
      const others = Object.entries(skillUses).filter(([called]) => !f.siaSkills.some((s) => skillMatches(called, s.name)))
      body = [
        Text({ key: 'h-sia', bold: true, children: ["Written by SIA from this project's requirements"] }),
        ...(f.siaSkills.length === 0
          ? [Text({ key: 'no-skills', dimColor: true, children: ['None yet. SIA writes them at the skills stage.'] })]
          : f.siaSkills.map((s) =>
              Box({
                key: 'skill-' + s.name,
                flexDirection: 'column',
                children: [
                  Box({
                    flexDirection: 'row',
                    columnGap: 2,
                    children: [
                      Text({ color: 'cyan', children: [s.name] }),
                      Text({ dimColor: true, children: [usesOf(s.name) + ' this session · ' + (projectUses[s.name] ?? 0) + ' total'] }),
                    ],
                  }),
                  Text({ dimColor: true, children: ['  ' + clip(s.description, width - 2)] }),
                ],
              }),
            )),
        Text({ key: 'gap', children: [' '] }),
        Text({ key: 'h-other', bold: true, children: ['Other skills used this session'] }),
        ...(others.length === 0
          ? [Text({ key: 'no-other', dimColor: true, children: ['None yet.'] })]
          : others.map(([called, count]) => Text({ key: 'other-' + called, children: [called + '  ×' + count] }))),
      ]
    } else {
      body = [
        Text({ key: 'calls-hint', dimColor: true, children: ['Press Enter on a call to start a prompt that uses it.'] }),
        ...(siaTools.length === 0
          ? [Text({ key: 'no-tools', dimColor: true, children: ["SIA's tools are not connected in this session. Install the sia plugin."] })]
          : siaTools.map((t) =>
              Box({
                key: 'call-row-' + t.name,
                flexDirection: 'column',
                children: [
                  Button({
                    key: 'call-' + t.name,
                    label: shortTool(t.name),
                    plain: true,
                    onPress: async () => {
                      await $.prompt.fill({ text: "Use SIA's " + shortTool(t.name) + ' tool to ' })
                      await $.ui.close({ id: PANE })
                    },
                  }),
                  Text({ dimColor: true, children: ['  ' + clip(t.description.split(/(?<=\.)\s/)[0] ?? '', width - 2)] }),
                ],
              }),
            )),
        Text({ key: 'gap', children: [' '] }),
        Text({ key: 'cmds', dimColor: true, children: ['Dashboard: /sia-dashboard · /sia-dashboard band on|off'] }),
      ]
    }

    return Box({
      flexDirection: 'column',
      children: [header, tabs, Text({ children: [' '] }), ...body],
    })
  })
}
