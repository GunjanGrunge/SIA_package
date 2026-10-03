import { expect, mock, test } from 'claude-code/testing'

const SIA_FILES: Record<string, string> = {
  'config.json': JSON.stringify({ mode: 'orchestrator' }),
  'state.json': JSON.stringify({ current_stage: 'execution', completed_stages: [] }),
  'rules.json': JSON.stringify([{ status: 'active' }]),
  'skills.json': JSON.stringify([{ name: 'loss-monitoring', description: 'Track training and validation loss.', status: 'active' }]),
}

const PANE = {
  plugin: 'sia-dashboard',
  component: 'Pane',
  requestId: 'sia-dashboard',
  viewport: { columns: 120, rows: 40 },
  props: { title: 'SIA', isFocused: true, bodyColumns: 80, placement: 'inline', scroll: { offset: 0, bodyRows: 20 }, view: {} },
} as const

// Stubs for everything the mod asks Claude Code during session.start and refreshes.
function stubSession(on, opts: { sia: boolean; agents?: unknown[]; filled?: string[] }) {
  mock.clock(on)
  const saved = new Map<string, unknown>()
  on('store.get', ($, e) => ({ value: saved.get(e.key) }))
  on('store.set', ($, e) => {
    saved.set(e.key, e.value)
    return { value: undefined }
  })
  on('session.start', () => ({ cwd: '/work' }))
  on('session.cwd', () => ({ value: '/work' }))
  on('session.model', () => ({ value: 'claude-opus-5-5' }))
  on('session.usage', () => ({ value: { startedAt: 0, context: { tokens: 0, window: 1, percent: 0 }, rateLimits: [], cost: { usd: 1.25 } } }))
  on('agent.list', () => ({ value: opts.agents ?? [] }))
  on('fs.exists', ($, e) => ({ value: opts.sia && e.path.replace(/\\/g, '/') === '/work/.sia/state.json' }))
  on('fs.read', ($, e) => {
    const name = Object.keys(SIA_FILES).find((n) => e.path.endsWith('/.sia/' + n))
    return name && opts.sia ? { value: SIA_FILES[name] } : { deny: 'missing' }
  })
  on('tool.list', () => ({
    value: [
      { name: 'mcp__plugin_sia_sia__sia_next', description: 'Return the next action. More detail here.', mcp: true },
      { name: 'mcp__plugin_sia_sia__sia_skill_write', description: 'Write one project skill.', mcp: true },
      { name: 'Bash', description: 'Run a command.', mcp: false },
    ],
  }))
  on('command.register', () => ({ value: undefined }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  on('prompt.fill', ($, e) => {
    opts.filled?.push(e.text)
    return { isFilled: true }
  })
  on('tool.call', () => ({ result: 'ok' }))
  on('turn.step', async function* ($, e) {
    return {
      turnId: e.turnId,
      index: e.index,
      answer: '',
      toolUses: [],
      stopReason: 'end_turn',
      usage: { model: e.agentId ? 'claude-haiku-4-5-20251001' : 'claude-opus-5-5', input_tokens: 1_000_000, output_tokens: 100_000, cache_read_input_tokens: 0, cache_creation_input_tokens: 0 },
    }
  })
  return saved
}

async function step($, agentId?: string) {
  const stream = $.turn.step({ turnId: 't', index: 0, model: 'claude-opus-5-5', messageCount: 1, ...(agentId ? { agentId } : {}) })
  let next = await stream.next()
  while (next.done !== true) next = await stream.next()
  return next.value
}

test('measures subagent tokens, the saving, and project skill use', async ($, on) => {
  const filled: string[] = []
  const saved = stubSession(on, {
    sia: true,
    filled,
    agents: [{ id: 'a1', description: 'implement math', type: 'sia:sia-implementer', status: 'running' }],
  })
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })

  // One main-loop request and one subagent request on Haiku
  const result = await step($)
  expect(result.answer).toBe('')
  await step($, 'a1')
  // The subagent uses the project skill twice
  await $.tool.call({ tool: 'Skill', skill: 'loss-monitoring' })
  await $.tool.call({ tool: 'Skill', skill: 'superpowers:test-driven-development' })
  await $.tool.call({ tool: 'Skill', skill: 'loss-monitoring' })

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: 'execution  (orchestrator mode)' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: '1 running' })).toBeDefined()
  // haiku 1.0 + 0.5 = 1.5 vs opus-5-5 4.0 + 2.0 = 6.0
  expect(await ui.find({ type: 'Text', text: '~$4.50' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: '1.1M tokens' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: '1 written by SIA' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: '  2 uses this session' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: '  1 this session' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: '$1.25' })).toBeDefined()

  await ui.press({ key: 'tab-agents' })
  expect(await ui.find({ type: 'Text', text: /haiku-4-5\s+1\.1M/ })).toBeDefined()

  await ui.press({ key: 'tab-skills' })
  expect(await ui.find({ type: 'Text', text: '2 this session · 2 total' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: 'superpowers:test-driven-development  ×1' })).toBeDefined()
  expect(saved.get('uses:/work')).toEqual({ 'loss-monitoring': 2 })

  await ui.press({ key: 'tab-calls' })
  expect(await ui.find({ key: 'call-mcp__plugin_sia_sia__sia_next' })).toBeDefined()
  expect(await ui.find({ key: 'call-Bash' })).toBeUndefined()
  await ui.press({ key: 'call-mcp__plugin_sia_sia__sia_skill_write' })
  expect(filled).toEqual(["Use SIA's sia_skill_write tool to "])
  await ui.unmount()
})

test('the pane draws on the desktop app too', async ($, on) => {
  stubSession(on, { sia: true })
  await $.session.start({ surface: 'desktop', isInteractive: true, cwd: '/work' })
  const ui = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await ui.find({ type: 'Text', text: 'SIA' })).toBeDefined()
  await ui.unmount()
})

test('the band shows in a SIA project and can be turned off', async ($, on) => {
  stubSession(on, { sia: true })
  on('ui.render', () => ({ type: 'Text', props: {}, children: ['drawn by Claude Code'] }))
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })
  const band = { plugin: 'sia-dashboard', component: 'AbovePrompt', viewport: { columns: 120, rows: 40 }, props: { hasSurvey: false, isWorking: false, maxRows: 4, bodyColumns: 100, scroll: { offset: 0, bodyRows: 4 }, view: {} } } as const
  let ui = await $.ui.mount({ ...band, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /^execution · 0 agents running · .* · 1 skill · 1 rule/ })).toBeDefined()
  await ui.unmount()

  const answer = await $.command.run({ command: 'sia-dashboard', args: 'band off' })
  expect(answer.text).toBe('SIA band above the prompt is off.')
  ui = await $.ui.mount({ ...band, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /agents running/ })).toBeUndefined()
  await ui.unmount()
})

test('outside a SIA project the band stays empty and the pane says how to start', async ($, on) => {
  stubSession(on, { sia: false })
  on('ui.render', () => ({ type: 'Text', props: {}, children: ['drawn by Claude Code'] }))
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })
  const band = await $.ui.mount({ plugin: 'sia-dashboard', component: 'AbovePrompt', surface: 'terminal', viewport: { columns: 120, rows: 40 }, props: { hasSurvey: false, isWorking: false, maxRows: 4, bodyColumns: 100, scroll: { offset: 0, bodyRows: 4 }, view: {} } })
  expect(await band.find({ type: 'Text', text: /agents running/ })).toBeUndefined()
  await band.unmount()
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /not set up here/ })).toBeDefined()
  await ui.unmount()
})

test('a finished subagent stays on the dashboard', async ($, on) => {
  const agents = [{ id: 'a1', description: 'scan files', type: 'Explore', status: 'running' }]
  stubSession(on, { sia: true, agents })
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/work' })
  await step($, 'a1')
  // Claude Code's list drops the agent once it finishes
  agents.length = 0
  await $.command.run({ command: 'sia-dashboard', args: '' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: '0 running' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: '  1 this session' })).toBeDefined()
  await ui.press({ key: 'tab-agents' })
  expect(await ui.find({ type: 'Text', text: /Explore: scan files/ })).toBeDefined()
  await ui.unmount()
})
