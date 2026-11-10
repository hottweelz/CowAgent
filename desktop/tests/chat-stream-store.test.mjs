import { test } from 'node:test'
import assert from 'node:assert/strict'
import { build } from 'esbuild'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const stubs = {
  '../api/client': `const apiClient = {
    sendMessage: async (sid) => ({ status: 'success', stream: true, request_id: sid }),
    createSSEStream: (id) => { const es = { close() {} }; globalThis.__chatStreams[id] = es; return es },
  }; export default apiClient;`,
  './workspaceStore': `export const useWorkspaceStore = { getState: () => ({ resetTurnArtifacts() {}, maybeAutoOpen() {}, addTurnArtifact() {} }) };`,
  './sessionStore': `export const sessionOwner = () => '';`,
  './sessionSettingsStore': `export const cfgFor = () => ({}); export const selectSharedConversation = () => false;`,
  './agentStore': `export const findAgent = () => undefined;`,
  '../lib/taskNotify': `export const notifyRunDone = () => {};`,
  '../lib/fileKind': `export const parseAttachmentMarkers = () => [];`,
  '../lib/handoff': `export const handoffPayload = () => undefined;`,
  '../i18n': `export const t = (key) => key;`,
}
const stubPlugin = {
  name: 'chat-store-boundary-stubs',
  setup(buildApi) {
    buildApi.onResolve({ filter: /.*/ }, (args) => args.kind === 'import-statement' && stubs[args.path]
      ? { path: args.path, namespace: 'chat-stub' }
      : undefined)
    buildApi.onLoad({ filter: /.*/, namespace: 'chat-stub' }, (args) => ({ contents: stubs[args.path], loader: 'js' }))
  },
}
const { outputFiles } = await build({
  stdin: { contents: `export { useChatStore } from './src/renderer/src/store/chatStore.ts'`, resolveDir: root },
  bundle: true, write: false, platform: 'node', format: 'esm', plugins: [stubPlugin],
})
const moduleUrl = `data:text/javascript;base64,${Buffer.from(outputFiles[0].text).toString('base64')}`
const { useChatStore } = await import(moduleUrl)

const frames = new Map()
let nextFrame = 0
globalThis.__chatStreams = {}
globalThis.requestAnimationFrame = (callback) => { const id = ++nextFrame; frames.set(id, callback); return id }
globalThis.cancelAnimationFrame = (id) => frames.delete(id)

async function openStream(sid) {
  await useChatStore.getState().send(sid, 'hello', [])
  return { es: globalThis.__chatStreams[sid], messages: () => useChatStore.getState().getSession(sid).messages }
}

function emit(es, event) {
  es.onmessage({ data: JSON.stringify(event) })
}

function flushFrames() {
  const callbacks = [...frames.values()]
  frames.clear()
  callbacks.forEach((callback) => callback(0))
}

test('real chat store commits a frame batch once and keeps interleaved event order', async () => {
  const { es, messages } = await openStream('batch-session')
  const assistant = messages().find((message) => message.role === 'assistant')
  let commits = 0
  const unsubscribe = useChatStore.subscribe(() => commits++)

  for (let i = 0; i < 10; i++) {
    emit(es, { type: 'reasoning', content: `r${i};` })
    emit(es, { type: 'delta', content: `d${i};` })
  }
  flushFrames()

  unsubscribe()
  assert.equal(commits, 1)
  const final = messages().find((message) => message.id === assistant.id)
  assert.equal(final.reasoning, 'r0;r1;r2;r3;r4;r5;r6;r7;r8;r9;')
  assert.equal(final.content, 'd0;d1;d2;d3;d4;d5;d6;d7;d8;d9;')
  emit(es, { type: 'error', message: 'close fixture' })
})

test('parallel sessions retain separate targets and pending text flushes before tool_end', async () => {
  const first = await openStream('first-session')
  const second = await openStream('second-session')
  const firstBot = first.messages().find((message) => message.role === 'assistant')
  const secondBot = second.messages().find((message) => message.role === 'assistant')

  emit(first.es, { type: 'reasoning', content: 'before tool ' })
  emit(first.es, { type: 'tool_start', tool_call_id: 'tool-1', tool: 'read', arguments: {} })
  emit(first.es, { type: 'tool_progress', tool_call_id: 'tool-1', content: 'old' })
  emit(first.es, { type: 'tool_progress', tool_call_id: 'tool-1', content: 'latest' })
  emit(second.es, { type: 'delta', content: 'other session' })
  emit(first.es, { type: 'tool_end', tool_call_id: 'tool-1', status: 'success', result: 'done' })

  flushFrames()
  const firstResult = first.messages().find((message) => message.id === firstBot.id)
  const secondResult = second.messages().find((message) => message.id === secondBot.id)
  assert.equal(firstResult.steps.find((step) => step.type === 'tool').result, 'done')
  assert.equal(firstResult.steps.find((step) => step.type === 'thinking').content, 'before tool')
  assert.equal(secondResult.content, 'other session')

  emit(first.es, { type: 'error', message: 'close fixture' })
  emit(second.es, { type: 'error', message: 'close fixture' })
})

test('peer transition and terminal done flush queued text before changing the speaking bubble', async () => {
  const { es, messages } = await openStream('terminal-session')
  emit(es, { type: 'delta', content: 'owner answer' })
  emit(es, { type: 'peer_start', agent_id: 'peer-1' })
  const peer = messages().at(-1)
  emit(es, { type: 'reasoning', content: 'peer thought' })
  emit(es, { type: 'delta', content: 'peer answer' })
  emit(es, { type: 'peer_end' })
  emit(es, { type: 'delta', content: 'owner resumed' })
  emit(es, { type: 'done', content: 'owner final' })

  const all = messages()
  assert.equal(all.find((message) => message.role === 'assistant' && message.content === 'owner final')?.content, 'owner final')
  const peerResult = all.find((message) => message.id === peer.id)
  assert.equal(peerResult.reasoning, 'peer thought')
  assert.equal(peerResult.content, 'peer answer')
  assert.equal(peerResult.isStreaming, false)
  assert.equal(all.find((message) => message.content === 'owner final').isStreaming, false)
  emit(es, { type: 'voice_attach' })
})
