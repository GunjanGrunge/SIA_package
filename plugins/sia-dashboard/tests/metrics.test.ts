import { expect, test } from 'claude-code/testing'
import { costOf, fmtTokens, fmtUsd, isSiaTool, priceFor, record, savings, shortModel, shortTool, siaSnapshot, skillMatches, type Ledger } from '../hooks/metrics.ts'

test('list prices match full ids, dated ids and aliases', async () => {
  expect(priceFor('claude-opus-5-5')).toMatchObject({ input: 4, output: 20, cacheRead: 0.2 })
  expect(priceFor('claude-haiku-4-5-20251001')).toMatchObject({ input: 1, output: 5 })
  expect(priceFor('claude-sonnet-5')).toMatchObject({ input: 2, output: 10 })
  // claude-opus-5 must not be priced as claude-opus-5-5
  expect(priceFor('claude-opus-5')).toMatchObject({ input: 5, output: 25 })
  expect(priceFor('haiku')).toMatchObject({ input: 1 })
  expect(priceFor('some-other-model')).toBeUndefined()
})

test('prices configured in SIA win, matched by alias', async () => {
  const overrides = { haiku: { input: 0.8, output: 4 } }
  expect(priceFor('claude-haiku-4-5-20251001', overrides)).toMatchObject({ input: 0.8, output: 4 })
  // A zero-priced tier falls back to list prices instead of making work look free.
  expect(priceFor('claude-haiku-4-5', { haiku: { input: 0, output: 0 } })).toMatchObject({ input: 1 })
})

test('cost counts every kind of token', async () => {
  const p = priceFor('claude-haiku-4-5')!
  const usage = { input_tokens: 1_000_000, output_tokens: 1_000_000, cache_read_input_tokens: 1_000_000, cache_creation_input_tokens: 1_000_000 }
  expect(costOf(usage, p)).toBe(1 + 5 + 0.1 + 1.25)
})

test('the saving prices subagent tokens at the main model and ignores the main loop', async () => {
  const ledger: Ledger = {}
  record(ledger, 'main', 'claude-opus-5-5', { input_tokens: 500_000, output_tokens: 0 })
  record(ledger, 'a1', 'claude-haiku-4-5-20251001', { input_tokens: 1_000_000, output_tokens: 100_000 })
  record(ledger, 'a2', 'claude-opus-5-5', { input_tokens: 10_000, output_tokens: 0 })
  const s = savings(ledger, 'claude-opus-5-5')
  expect(s.subagentTokens).toBe(1_110_000)
  expect(s.routedTokens).toBe(1_100_000)
  // haiku: 1.0 + 0.5 = 1.5; at opus-5-5 prices: 4.0 + 2.0 = 6.0
  expect(s.routedCost).toBe(1.5)
  expect(s.baselineCost).toBe(6)
  expect(s.saved).toBe(4.5)
})

test('a subagent on a pricier model shows a negative saving', async () => {
  const ledger: Ledger = {}
  record(ledger, 'a1', 'claude-fable-5-1', { input_tokens: 1_000_000, output_tokens: 0 })
  expect(savings(ledger, 'claude-sonnet-5').saved).toBe(2 - 10)
})

test('an unknown model is reported, not guessed', async () => {
  const ledger: Ledger = {}
  record(ledger, 'a1', 'mystery-1', { input_tokens: 1000, output_tokens: 0 })
  const s = savings(ledger, 'claude-opus-5-5')
  expect(s.unpriced).toEqual(['mystery-1'])
  expect(s.saved).toBe(0)
})

test('reads SIA state, counting only active rules', async () => {
  const snap = siaSnapshot('/p', {
    config: JSON.stringify({ mode: 'orchestrator', orchestration: { models: { cheap: { id: 'haiku', input_usd_per_million: 1, output_usd_per_million: 5 } } } }),
    state: JSON.stringify({ current_stage: 'execution', completed_stages: ['intake'], orchestration: { status: 'running', operations: { a: { status: 'complete' }, b: { status: 'ready' } } } }),
    rules: JSON.stringify([{ status: 'active' }, { status: 'retired' }, { status: 'active' }]),
    skills: JSON.stringify([{ name: 'loss-monitoring', description: 'Track loss.', status: 'active', version: 2 }]),
  })
  expect(snap.stage).toBe('execution')
  expect(snap.rules).toBe(2)
  expect(snap.skills[0]).toMatchObject({ name: 'loss-monitoring', status: 'active' })
  expect(snap.operations).toEqual({ total: 2, complete: 1, status: 'running' })
  expect(snap.overrides.haiku).toEqual({ input: 1, output: 5 })
})

test('broken or missing SIA files read as empty', async () => {
  const snap = siaSnapshot('/p', { config: '{not json', state: undefined })
  expect(snap.rules).toBe(0)
  expect(snap.skills).toEqual([])
  expect(snap.operations).toBeUndefined()
})

test('helpers', async () => {
  expect(skillMatches('loss-monitoring', 'loss-monitoring')).toBe(true)
  expect(skillMatches('proj:loss-monitoring', 'loss-monitoring')).toBe(true)
  expect(skillMatches('loss-monitoring-v2', 'loss-monitoring')).toBe(false)
  expect(isSiaTool('mcp__plugin_sia_sia__sia_next')).toBe(true)
  expect(isSiaTool('mcp__sia__sia_skill_write')).toBe(true)
  expect(isSiaTool('mcp__github__create_issue')).toBe(false)
  expect(shortTool('mcp__plugin_sia_sia__sia_orchestrate_plan')).toBe('sia_orchestrate_plan')
  expect(shortModel('claude-haiku-4-5-20251001')).toBe('haiku-4-5')
  expect(fmtTokens(48_200)).toBe('48k')
  expect(fmtTokens(4_820)).toBe('4.8k')
  expect(fmtUsd(0.4234)).toBe('$0.423')
  expect(fmtUsd(-2)).toBe('-$2.00')
})
