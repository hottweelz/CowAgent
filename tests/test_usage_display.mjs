import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'

const labels = {
  msg_usage_total: 'Run total',
  msg_usage_in: 'In',
  msg_usage_out: 'Out',
  msg_usage_cached: 'Cached',
  msg_usage_calls: '{n} model calls',
  msg_usage_cache_unknown: 'Cache usage unknown',
  msg_usage_cache_partial: 'Cache reported on {reported}/{calls} calls ({tokens} tokens)',
  msg_usage_partial: 'Partial usage (input reported for {inputReported}/{inputTotal} calls; output for {outputReported}/{outputTotal})',
  msg_usage_unknown: 'Usage unknown',
}

function declaration(source, name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const match = source.match(new RegExp(`function ${escaped}\\([\\s\\S]*?\\n\\}`))
  assert.ok(match, `missing ${name} declaration`)
  return match[0]
}

function runtime(functions) {
  const context = {
    t: (key) => labels[key] || key,
    tf: (key, values) => Object.entries(values).reduce(
      (value, [name, part]) => value.replace(`{${name}}`, String(part)),
      labels[key] || key,
    ),
    escapeHtml: (value) => String(value),
  }
  vm.createContext(context)
  vm.runInContext(functions.join('\n'), context)
  return context
}

const webSource = readFileSync(new URL('../channel/web/static/js/chat/render.js', import.meta.url), 'utf8')
const web = runtime([
  declaration(webSource, 'messageUsageCompletenessLabel'),
  declaration(webSource, 'messageCacheUsageLabel'),
  declaration(webSource, 'renderMessageUsageHtml'),
])

const desktopSource = readFileSync(
  new URL('../desktop/src/renderer/src/components/MessageBubble.tsx', import.meta.url),
  'utf8',
)
const desktop = runtime([
  declaration(desktopSource, 'messageUsageCompletenessLabel')
    .replace('function messageUsageCompletenessLabel(usage: MessageUsage, calls: number): string {',
      'function messageUsageCompletenessLabel(usage, calls) {'),
  declaration(desktopSource, 'messageCacheUsageLabel')
    .replace('function messageCacheUsageLabel(usage: MessageUsage, input: number, calls: number): string {',
      'function messageCacheUsageLabel(usage, input, calls) {'),
  declaration(desktopSource, 'usageLabel')
    .replace('function usageLabel(usage?: MessageUsage): string {', 'function usageLabel(usage) {')
    .replace('const n = (v?: number) =>', 'const n = (v) =>'),
])

const contextLabels = {
  ctx_request_latest: 'Latest request (actual usage)',
  ctx_request_input: 'Input',
  ctx_request_output: 'Output',
  ctx_request_unknown: 'Unknown',
  ctx_request_partial: 'reported on {reported}/{calls} calls',
}
const contextRuntime = (functions) => {
  const context = { t: (key) => contextLabels[key] || key }
  vm.createContext(context)
  vm.runInContext(functions.join('\n'), context)
  return context
}
const contextWeb = contextRuntime([
  declaration(readFileSync(new URL('../channel/web/static/js/chat/context-usage.js', import.meta.url), 'utf8'), '_ctxFmtTokens'),
  declaration(readFileSync(new URL('../channel/web/static/js/chat/context-usage.js', import.meta.url), 'utf8'), '_ctxLatestRequestUsageHtml'),
])
const contextDesktop = contextRuntime([
  declaration(readFileSync(new URL('../desktop/src/renderer/src/components/ContextUsagePopover.tsx', import.meta.url), 'utf8'), 'latestRequestTokenValue')
    .replace('function latestRequestTokenValue(\n  usage: NonNullable<NonNullable<ContextUsage[\'last_request\']>[\'usage\']> | undefined,\n  tokenKey: \'prompt_tokens\' | \'completion_tokens\',\n  coverageKey: \'prompt_tokens_reported_calls\' | \'completion_tokens_reported_calls\',\n): { value: number | null; reported: number | null; calls: number | null } {',
      'function latestRequestTokenValue(usage, tokenKey, coverageKey) {'),
])

for (const [name, surface] of [['web', web], ['desktop', desktop]]) {
  test(`${name} distinguishes unknown, explicit zero, partial and legacy cache usage`, () => {
    assert.equal(surface.messageCacheUsageLabel({}, 100, 1), 'Cache usage unknown')
    assert.equal(surface.messageCacheUsageLabel({
      prompt_cache_hit_tokens: 0, prompt_cache_hit_tokens_reported_calls: 1,
    }, 100, 1), 'Cached 0%')
    assert.match(surface.messageCacheUsageLabel({
      prompt_cache_hit_tokens: 40, prompt_cache_hit_tokens_reported_calls: 1,
    }, 100, 2), /Cache reported on 1\/2 calls \(40 tokens\)/)
    assert.equal(surface.messageCacheUsageLabel({prompt_cache_hit_tokens: 40}, 100, 1), 'Cached 40%')
  })
}

test('web tooltip labels known subtotals when request usage is partial', () => {
  const html = web.renderMessageUsageHtml({
    prompt_tokens: 1200,
    completion_tokens: 80,
    total_tokens: 1280,
    prompt_tokens_reported_calls: 1,
    completion_tokens_reported_calls: 2,
    calls: 2,
  })
  assert.match(html, /Partial usage \(input reported for 1\/2 calls; output for 2\/2\)/)
  assert.match(html, /Run total 1,280/)
})

test('web tooltip shows unknown when all usage counts are zero and unreported', () => {
  const html = web.renderMessageUsageHtml({
    prompt_tokens: 0,
    completion_tokens: 0,
    total_tokens: 0,
    calls: 1,
  })
  assert.match(html, /Usage unknown/)
})

for (const [name, surface] of [['web', contextWeb], ['desktop', contextDesktop]]) {
  test(`${name} context card shows only reported latest-request counts`, () => {
    if (name === 'web') {
      const html = surface._ctxLatestRequestUsageHtml({ usage: {
        prompt_tokens: 10271, prompt_tokens_reported_calls: 1,
        completion_tokens: 0, completion_tokens_reported_calls: 1, calls: 1,
      } })
      assert.match(html, /Latest request \(actual usage\)/)
      assert.match(html, /10,271/)
      assert.match(html, />0</)
      assert.doesNotMatch(surface._ctxLatestRequestUsageHtml({ usage: { prompt_tokens: 0, calls: 1 } }), />0</)
      assert.match(surface._ctxLatestRequestUsageHtml({ usage: {
        prompt_tokens: 10, prompt_tokens_reported_calls: 1, calls: 2,
      } }), /reported on 1\/2 calls/)
    } else {
      assert.deepEqual(JSON.parse(JSON.stringify(surface.latestRequestTokenValue({
        prompt_tokens: 10271, prompt_tokens_reported_calls: 1, calls: 1,
      }, 'prompt_tokens', 'prompt_tokens_reported_calls'))),
      { value: 10271, reported: 1, calls: 1 })
      assert.equal(surface.latestRequestTokenValue({ prompt_tokens: 0, calls: 1 },
        'prompt_tokens', 'prompt_tokens_reported_calls').value, null)
      assert.equal(surface.latestRequestTokenValue({ prompt_tokens: 0,
        prompt_tokens_reported_calls: 1, calls: 1 }, 'prompt_tokens', 'prompt_tokens_reported_calls').value, 0)
    }
  })
}

test('desktop tooltip labels known subtotals when request usage is partial', () => {
  const label = desktop.usageLabel({
    prompt_tokens: 1200,
    completion_tokens: 80,
    total_tokens: 1280,
    prompt_tokens_reported_calls: 1,
    completion_tokens_reported_calls: 2,
    calls: 2,
  })
  assert.match(label, /Partial usage \(input reported for 1\/2 calls; output for 2\/2\)/)
  assert.match(label, /Run total 1,280/)
})

test('desktop tooltip shows unknown when all usage counts are zero and unreported', () => {
  const label = desktop.usageLabel({
    prompt_tokens: 0,
    completion_tokens: 0,
    total_tokens: 0,
    calls: 1,
  })
  assert.match(label, /Usage unknown/)
})
