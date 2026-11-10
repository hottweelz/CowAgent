import { test } from 'node:test'
import assert from 'node:assert/strict'
import { build } from 'esbuild'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const dir = await mkdtemp(path.join(tmpdir(), 'cow-stream-batch-'))
const outfile = path.join(dir, 'stream-batch.mjs')
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
await build({
  stdin: { contents: `export { StreamBatch } from './src/renderer/src/lib/streamBatch.ts';`, resolveDir: root },
  outfile, bundle: true, platform: 'node', format: 'esm',
})
const { StreamBatch } = await import(pathToFileURL(outfile))
test.after(() => rm(dir, { recursive: true, force: true }))

function fixture() {
  const callbacks = new Map()
  const commits = []
  let nextFrame = 0
  const batch = new StreamBatch(
    (items) => commits.push(items),
    (callback) => { const id = ++nextFrame; callbacks.set(id, callback); return id },
    (id) => callbacks.delete(id),
  )
  return {
    batch, commits,
    frame() { const [id, callback] = callbacks.entries().next().value || []; if (callback) { callbacks.delete(id); callback(0) } },
  }
}

test('reasoning and answer text preserve order and stay bound to their message target', () => {
  const { batch, commits, frame } = fixture()
  batch.reasoning('owner-message', 'think ')
  batch.reasoning('owner-message', 'more')
  batch.delta('owner-message', 'answer')
  batch.reasoning('peer-message', 'peer thought')
  frame()

  assert.deepEqual(commits, [[
    { type: 'reasoning', target: 'owner-message', content: 'think more' },
    { type: 'delta', target: 'owner-message', content: 'answer' },
    { type: 'reasoning', target: 'peer-message', content: 'peer thought' },
  ]])
})

test('progress retains only the latest value per card and does not drop other cards', () => {
  const { batch, commits, frame } = fixture()
  batch.progress('tool-a', 'first')
  batch.progress('tool-b', 'other card')
  batch.progress('tool-a', 'latest')
  frame()

  assert.deepEqual(commits, [[
    { type: 'tool_progress', toolCallId: 'tool-a', content: 'latest' },
    { type: 'tool_progress', toolCallId: 'tool-b', content: 'other card' },
  ]])
})

test('synchronous flush cancels a pending frame and preserves terminal-event text', () => {
  const { batch, commits, frame } = fixture()
  batch.delta('message-a', 'final answer')
  batch.progress('tool-a', 'final output')
  batch.flush() // The chat store does this before tool_end/message_end and other transitions.
  frame()

  assert.deepEqual(commits, [[
    { type: 'delta', target: 'message-a', content: 'final answer' },
    { type: 'tool_progress', toolCallId: 'tool-a', content: 'final output' },
  ]])
})
