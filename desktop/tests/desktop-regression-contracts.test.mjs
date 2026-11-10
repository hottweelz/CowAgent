import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const read = (file) => readFile(path.join(root, file), 'utf8')

test('memoized message bubbles still update for language changes and edited agents', async () => {
  const [bubble, page] = await Promise.all([
    read('src/renderer/src/components/MessageBubble.tsx'),
    read('src/renderer/src/pages/ChatPage.tsx'),
  ])
  assert.match(bubble, /export default React\.memo\(MessageBubble\)/)
  assert.match(bubble, /useAgentStore\(\(s\) => \(speakerId \? s\.agents\.find\(\(a\) => a\.id === speakerId\) : undefined\)\)/)
  assert.match(page, /lang=\{getLang\(\)\}/)
})

test('window recovery preserves normal bounds and detaches display listeners on close', async () => {
  const source = await read('src/main/index.ts')
  assert.match(source, /mainWindow\.isMaximized\(\) \? mainWindow\.getNormalBounds\(\) : mainWindow\.getBounds\(\)/)
  assert.match(source, /win\.isDestroyed\(\) \|\| win\.isMinimized\(\) \|\| win\.isFullScreen\(\)/)
  assert.match(source, /screen\.on\('display-removed', recheck\)/)
  assert.match(source, /screen\.on\('display-metrics-changed', recheck\)/)
  assert.match(source, /mainWindow\.on\('closed', \(\) => \{[\s\S]*screen\.removeListener\('display-removed', recheck\)[\s\S]*screen\.removeListener\('display-metrics-changed', recheck\)/)
})
