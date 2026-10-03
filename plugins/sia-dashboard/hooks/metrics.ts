// Pure logic for the SIA dashboard: prices, token ledger, savings, and reading
// SIA's state files. Nothing here touches the mods API, so tests import it
// directly.

export type Usage = {
  input_tokens: number
  output_tokens: number
  cache_read_input_tokens?: number
  cache_creation_input_tokens?: number
}

/** USD per million tokens. */
export type Price = { input: number; output: number; cacheRead: number; cacheWrite: number }

const price = (input: number, output: number, cacheRead: number): Price => ({
  input,
  output,
  cacheRead,
  // A 5-minute cache write costs 1.25x the input price on every current model.
  cacheWrite: input * 1.25,
})

// Anthropic first-party list prices, per million tokens (checked 2026-10-03).
// Most specific prefix first: model ids can carry a date suffix, such as
// claude-haiku-4-5-20251001, and short aliases (haiku, sonnet, opus) appear too.
const LIST_PRICES: [string, Price][] = [
  ['claude-fable-5-1', price(10, 50, 0.25)],
  ['claude-mythos-5-1', price(10, 50, 0.25)],
  ['claude-fable-5', price(10, 50, 1)],
  ['claude-opus-5-5', price(4, 20, 0.2)],
  ['claude-opus-5', price(5, 25, 0.5)],
  ['claude-opus-4', price(5, 25, 0.5)],
  ['claude-sonnet-5-5', price(2, 10, 0.2)],
  ['claude-sonnet-5', price(2, 10, 0.2)],
  ['claude-sonnet-4', price(3, 15, 0.3)],
  ['claude-haiku-4-5', price(1, 5, 0.1)],
  ['fable', price(10, 50, 0.25)],
  ['opus', price(4, 20, 0.2)],
  ['sonnet', price(2, 10, 0.2)],
  ['haiku', price(1, 5, 0.1)],
]

/** Prices a project configured in SIA's orchestration tiers, keyed by model id. */
export type PriceOverrides = Record<string, { input: number; output: number }>

export function priceFor(model: string, overrides: PriceOverrides = {}): Price | undefined {
  const id = model.toLowerCase().replace(/\[.*\]$/, '')
  // SIA configs often name a tier by alias (haiku), while usage reports the
  // full id (claude-haiku-4-5-20251001), so an alias also matches its family.
  const alias = Object.keys(overrides).find((key) => /^[a-z]+$/.test(key) && id.includes('-' + key + '-'))
  const own = overrides[id] ?? overrides[model] ?? (alias ? overrides[alias] : undefined)
  if (own && (own.input > 0 || own.output > 0)) {
    // SIA's config holds input and output prices only; cache rates follow the
    // usual ratios.
    return { input: own.input, output: own.output, cacheRead: own.input * 0.1, cacheWrite: own.input * 1.25 }
  }
  const found = LIST_PRICES.find(([prefix]) => id === prefix || id.startsWith(prefix + '-') || id.startsWith(prefix + '['))
  return found?.[1]
}

export function costOf(usage: Usage, p: Price): number {
  return (
    (usage.input_tokens * p.input +
      usage.output_tokens * p.output +
      (usage.cache_read_input_tokens ?? 0) * p.cacheRead +
      (usage.cache_creation_input_tokens ?? 0) * p.cacheWrite) /
    1_000_000
  )
}

export function totalTokens(usage: Usage): number {
  return (
    usage.input_tokens +
    usage.output_tokens +
    (usage.cache_read_input_tokens ?? 0) +
    (usage.cache_creation_input_tokens ?? 0)
  )
}

/** Token use per agent loop and model. 'main' is the main conversation. */
export type Ledger = Record<string, Record<string, Usage & { requests: number }>>

export function record(ledger: Ledger, loop: string, model: string, usage: Usage): void {
  const byModel = (ledger[loop] ??= {})
  const row = (byModel[model] ??= {
    input_tokens: 0,
    output_tokens: 0,
    cache_read_input_tokens: 0,
    cache_creation_input_tokens: 0,
    requests: 0,
  })
  row.input_tokens += usage.input_tokens
  row.output_tokens += usage.output_tokens
  row.cache_read_input_tokens = (row.cache_read_input_tokens ?? 0) + (usage.cache_read_input_tokens ?? 0)
  row.cache_creation_input_tokens = (row.cache_creation_input_tokens ?? 0) + (usage.cache_creation_input_tokens ?? 0)
  row.requests += 1
}

export type Savings = {
  /** Tokens processed inside subagents, which never entered the main conversation. */
  subagentTokens: number
  /** Of those, tokens processed on a model other than the main one. */
  routedTokens: number
  /** What the routed tokens cost on the models they ran on. */
  routedCost: number
  /** What the same tokens would have cost on the main model. */
  baselineCost: number
  /** baselineCost - routedCost. Negative when subagents ran on a pricier model. */
  saved: number
  /** Models seen without a known price; their tokens are left out of the cost figures. */
  unpriced: string[]
}

/**
 * Estimated saving from running subagents on cheaper models: each subagent
 * request priced at the main model's rates minus its price on the model it
 * actually ran on. It assumes the main model would have used the same tokens,
 * which is an estimate, so the dashboard labels it as one.
 */
export function savings(ledger: Ledger, mainModel: string, overrides: PriceOverrides = {}): Savings {
  const base = priceFor(mainModel, overrides)
  const result: Savings = { subagentTokens: 0, routedTokens: 0, routedCost: 0, baselineCost: 0, saved: 0, unpriced: [] }
  for (const [loop, byModel] of Object.entries(ledger)) {
    if (loop === 'main') continue
    for (const [model, usage] of Object.entries(byModel)) {
      const tokens = totalTokens(usage)
      result.subagentTokens += tokens
      if (sameModel(model, mainModel)) continue
      const actual = priceFor(model, overrides)
      if (!actual || !base) {
        if (!result.unpriced.includes(model)) result.unpriced.push(model)
        continue
      }
      result.routedTokens += tokens
      result.routedCost += costOf(usage, actual)
      result.baselineCost += costOf(usage, base)
    }
  }
  result.saved = result.baselineCost - result.routedCost
  return result
}

export function sameModel(a: string, b: string): boolean {
  const norm = (m: string) => m.toLowerCase().replace(/\[.*\]$/, '').replace(/-\d{8}$/, '')
  return norm(a) === norm(b)
}

export function loopTokens(ledger: Ledger, loop: string): number {
  return Object.values(ledger[loop] ?? {}).reduce((sum, usage) => sum + totalTokens(usage), 0)
}

export function loopModels(ledger: Ledger, loop: string): string[] {
  return Object.keys(ledger[loop] ?? {})
}

// --- SIA state ---------------------------------------------------------------

export type SiaSkill = { name: string; description: string; status: string; version?: number }

export type SiaSnapshot = {
  root: string
  mode?: string
  stage?: string | null
  completed: string[]
  rules: number
  skills: SiaSkill[]
  operations?: { total: number; complete: number; status?: string }
  overrides: PriceOverrides
}

function parse(text: string | undefined): any {
  if (!text) return undefined
  try {
    return JSON.parse(text)
  } catch {
    return undefined
  }
}

/** Builds a snapshot from the raw text of SIA's files; a missing or broken file counts as empty. */
export function siaSnapshot(
  root: string,
  files: { config?: string; state?: string; rules?: string; skills?: string },
): SiaSnapshot {
  const config = parse(files.config) ?? {}
  const state = parse(files.state) ?? {}
  const rules = parse(files.rules)
  const skills = parse(files.skills)
  const overrides: PriceOverrides = {}
  for (const tier of Object.values(config.orchestration?.models ?? {}) as any[]) {
    if (tier && typeof tier.id === 'string') {
      overrides[tier.id.toLowerCase()] = {
        input: Number(tier.input_usd_per_million) || 0,
        output: Number(tier.output_usd_per_million) || 0,
      }
    }
  }
  const orchestration = state.orchestration
  const operations = orchestration?.operations
  return {
    root,
    mode: config.mode,
    stage: state.current_stage,
    completed: Array.isArray(state.completed_stages) ? state.completed_stages : [],
    rules: Array.isArray(rules) ? rules.filter((r: any) => r?.status === 'active').length : 0,
    skills: Array.isArray(skills)
      ? skills
          .filter((s: any) => s && typeof s.name === 'string')
          .map((s: any) => ({ name: s.name, description: String(s.description ?? ''), status: String(s.status ?? ''), version: s.version }))
      : [],
    operations:
      operations && typeof operations === 'object'
        ? {
            total: Object.keys(operations).length,
            complete: Object.values(operations).filter((o: any) => o?.status === 'complete').length,
            status: orchestration.status,
          }
        : undefined,
    overrides,
  }
}

/** True when a Skill tool call's `skill` names this project skill, plain or plugin-qualified. */
export function skillMatches(called: string, name: string): boolean {
  return called === name || called.endsWith(':' + name)
}

// --- formatting --------------------------------------------------------------

export function fmtTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(n >= 10_000_000 ? 0 : 1) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(n >= 10_000 ? 0 : 1) + 'k'
  return String(n)
}

export function fmtUsd(n: number): string {
  const sign = n < 0 ? '-' : ''
  const abs = Math.abs(n)
  return sign + '$' + (abs >= 100 ? abs.toFixed(0) : abs >= 1 ? abs.toFixed(2) : abs.toFixed(3))
}

/** claude-haiku-4-5-20251001 -> haiku-4-5 */
export function shortModel(model: string): string {
  return model.replace(/^claude-/, '').replace(/-\d{8}$/, '').replace(/\[.*\]$/, '')
}

export function clip(text: string, width: number): string {
  const flat = text.replace(/\s+/g, ' ').trim()
  return flat.length <= width ? flat : flat.slice(0, Math.max(0, width - 1)) + '…'
}

/** sia_orchestrate_plan from mcp__plugin_sia_sia__sia_orchestrate_plan */
export function shortTool(name: string): string {
  const at = name.lastIndexOf('__')
  return at >= 0 ? name.slice(at + 2) : name
}

export function isSiaTool(name: string): boolean {
  return name.startsWith('mcp__') && /__sia_[a-z_]+$/.test(name)
}
