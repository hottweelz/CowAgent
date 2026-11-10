# Desktop candidates 9 and 10

Baseline: `74b75f97`. This work ports desktop stream batching from upstream `b6cff3e2` / PR #3920 and off-screen recovery from `aa917a4a` / PR #3919.

## Changes

- Batch reasoning, answer deltas, and tool progress on animation frames. Keep text event order, keep each update bound to its target message, and retain only the latest progress value per tool card. Flush before other event types and on stream errors.
- Memoize `MessageBubble`. Pass the current language to invalidate the memoized bubble when the module-global translation changes. Subscribe to the matching agent profile so an edited name/avatar updates.
- Sanitize saved window bounds against display work areas. Recover hidden-offscreen windows on show and display changes. Keep maximized window restore bounds, skip relocation for minimized/full-screen windows, avoid saving off-screen positions, and remove screen listeners when the window closes.

## Deviations from upstream

- Extracted `StreamBatch` into `desktop/src/renderer/src/lib/streamBatch.ts` to make ordering, target, latest-progress, and synchronous-flush behavior directly testable. Store updates still use the same session-specific mutation paths.
- Extracted display geometry helpers into `desktop/src/main/windowBounds.ts` so saved-state sanitization, secondary-display visibility, and recovery placement can be tested without starting Electron.
- Used the English-comment form of the window candidate (the local `aa917a4a` has Chinese comments); functional behavior matches PR #3919's `45eeddee` head.

## Verification

- `npm run build` — passed renderer Vite build and main TypeScript build.
- `npx tsc --noEmit -p tsconfig.json` — passed strict renderer typecheck.
- `node --test tests/*.test.mjs` — 13 passed, including existing chat-scroll tests and new stream-batch, window-bounds, and source-wiring regression tests.
- `git diff --check` — expected to be run by the parent during integration review.

The renderer build reports existing missing optional font CSS, stale Browserslist data, a mixed static/dynamic import warning, and a large-chunk warning. No live app launch or window-manager interaction was run. Source-wiring tests check show/display listener registration and cleanup text; real Electron event delivery and display disconnect behavior remain unverified in this headless run.

## Files

- `desktop/src/renderer/src/lib/streamBatch.ts`
- `desktop/src/renderer/src/store/chatStore.ts`
- `desktop/src/renderer/src/components/MessageBubble.tsx`
- `desktop/src/renderer/src/pages/ChatPage.tsx`
- `desktop/src/main/windowBounds.ts`
- `desktop/src/main/index.ts`
- `desktop/tests/stream-batch.test.mjs`
- `desktop/tests/window-bounds.test.mjs`
- `desktop/tests/desktop-regression-contracts.test.mjs`
