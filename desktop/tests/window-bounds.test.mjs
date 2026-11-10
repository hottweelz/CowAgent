import { test } from 'node:test'
import assert from 'node:assert/strict'
import { build } from 'esbuild'
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const dir = await mkdtemp(path.join(tmpdir(), 'cow-window-bounds-'))
const outfile = path.join(dir, 'window-bounds.mjs')
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
await build({
  stdin: { contents: `export { isOnSomeDisplay, sanitizeWindowState, centeredVisibleBounds } from './src/main/windowBounds.ts';`, resolveDir: root },
  outfile, bundle: true, platform: 'node', format: 'esm',
})
const { isOnSomeDisplay, sanitizeWindowState, centeredVisibleBounds } = await import(pathToFileURL(outfile))
test.after(() => rm(dir, { recursive: true, force: true }))

const display = (x, y, width, height) => ({ workArea: { x, y, width, height } })
const screenFor = (displays, primary = displays[0]) => ({ getAllDisplays: () => displays, getPrimaryDisplay: () => primary })

test('drops a saved position outside displays and clamps dimensions to primary work area', () => {
  const screen = screenFor([display(0, 0, 1280, 700)])
  assert.deepEqual(sanitizeWindowState({ x: 9991, y: 9991, width: 1920, height: 1032 }, screen), { width: 1280, height: 700 })
})

test('preserves a saved position that remains visible on a secondary display', () => {
  const screen = screenFor([display(0, 0, 1280, 800), display(1280, 0, 1600, 900)])
  assert.deepEqual(sanitizeWindowState({ x: 1400, y: 100, width: 1500, height: 850 }, screen), { x: 1400, y: 100, width: 1500, height: 850 })
})

test('requires 100 visible pixels in both dimensions and centers a disconnected window', () => {
  const screen = screenFor([display(0, 0, 1200, 800)])
  assert.equal(isOnSomeDisplay({ x: 1100, y: 0, width: 500, height: 500 }, screen), true)
  assert.equal(isOnSomeDisplay({ x: 1101, y: 0, width: 500, height: 500 }, screen), false)
  assert.deepEqual(centeredVisibleBounds({ x: 4000, y: 4000, width: 1500, height: 900 }, screen), { x: 0, y: 0, width: 1200, height: 800 })
})
