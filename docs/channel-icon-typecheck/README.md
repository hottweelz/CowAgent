# Channel icon type contract and release gate closure

Status: **verified; RELEASE READY for the documented restricted-mode scope**.
The maintainer authorized merging the verified integration into the fork's
master after the gates pass. Deployment and production restart are not included.

Branch: `fix/channels-icon-type-contract`, based on
`release/orchestration-release-001` at
`1a64afad5f7d54ff1f20e40eadb1d17370bc8e40`.
Product fix: [`9604bde7cacd19aeb914b345dcc5c9ea8616e0e4`](https://github.com/hottweelz/CowAgent/commit/9604bde7cacd19aeb914b345dcc5c9ea8616e0e4).

## Defect and minimal correction

The original strict check reproduced all nine TS2322 errors. The local
`React.FC<{ size?: number }>` alias compares static `propTypes` metadata as
well as the render call. Lucide's forward-ref components accept `size` as a
number or string, so their validator type is incompatible with the alias's
number-only validator. The actual calls always pass a number.

The alias now uses `React.JSXElementConstructor<{ size?: number }>`. This checks
the JSX call contract shared by the Lucide icons and the custom function-based
`PaperPlaneIcon`. The numeric size contract remains unchanged. There is no
cast, `any`, ignored diagnostic, dependency change, or TypeScript configuration
change. Strictness remains enabled. The emitted JavaScript before and after
the fix is byte-identical when comments are removed. Channel mappings, colors,
sizes, connection actions, state and API behavior are unchanged.

Installed versions checked: React 18.3.1, Lucide React 1.21.0, TypeScript 5.9.3.

## Gates rerun on 2026-11-07

| Gate | Result |
| --- | --- |
| `cd desktop && ./node_modules/.bin/tsc --noEmit -p tsconfig.json` | Pass, exit 0, zero errors; previous result was exit 2 with nine errors. |
| `cd desktop && npm run build` | Pass; renderer and Electron main build. |
| Node usage display, scroll and message-mutation suites | 39 passed. |
| Full isolated orchestration release regression | 1,364 passed, 15 skipped across 119 Python test files. |
| Seven native-browser cases, rerun separately | All seven passed; exact IDs match seven skipped cases above. |
| Deduplicated Python result | 1,371 passed, eight Windows-only skips, no failures/errors. |
| F-class Ruff and compilation | All 54 retained changed/new Python files passed; hashes match the reviewed integration. |
| Real ChannelsPage rendering and selection | 12 card icons and 12 dropdown icons passed; both paper-plane mappings and unknown-channel fallback checked. |
| Independent local type-contract review | Luna/high found no blocking issue; no broad review repeated. |

Receipts: [UI/build/typecheck](ui-gates.json), [Python/native-browser/static](python-gates.json),
[rendered DOM observations](rendering.json). The original failed strict check
remains preserved in the [historical report](../known-issues/channels-page-typecheck.md)
and the earlier release receipt; it has not been relabeled as a pass.

The browser ran the actual page and stylesheet through Vite, using synthetic
channel API data and a fresh Chrome context. It was allowed to request only
the owned localhost fixture. Observed API traffic was two GET requests to
`/api/channels`; no mutation or production backend was used. Assertions require
nonempty SVG geometry, correct glyph classes, matching paper-plane paths,
18-pixel card glyphs and 12-pixel dropdown glyphs. Real clicks open the add
panel, select Telegram, and close the panel. No page errors occurred.

The lead visually inspected all icons in light and settled dark themes and
the selected-channel state. No missing glyph, clipping or alignment defect was
seen. Screenshots: [light](channel-cards-light.png), [dark](channel-cards-dark.png),
[Telegram selected](telegram-selected.png). The dark capture waits for the
existing color transition to finish; class presence alone is insufficient.

## Reproduce the rendering check

Start the private fixture, which prints its localhost URL:

```bash
node docs/channel-icon-typecheck/render_fixture.mjs
```

The fixture imports `desktop/tests/channel-icons-fixture.tsx`, which mounts
the real `ChannelsPage`. It serves synthetic channel reads and rejects every
other API request. No CowAgent backend is started. From a Playwright session:

```javascript
const { verifyIcons } = await import('./docs/channel-icon-typecheck/verify_icons.mjs')
const context = await browser.newContext()
const fixtureUrl = 'http://127.0.0.1:5173/__channels' // use the printed URL
await context.route('**/*', route =>
  new URL(route.request().url()).origin === new URL(fixtureUrl).origin
    ? route.continue() : route.abort())
const page = await context.newPage()
page.setDefaultTimeout(5000)
await verifyIcons(page, fixtureUrl, './docs/channel-icon-typecheck')
await context.close()
```

The review used the already installed Python Playwright package's Node driver
and system Chrome. No package or browser installation was needed. Fixture
server and owned browser were closed after checks.

## Limits and integration

Eight Windows path/PowerShell cases remain platform skips. Linux needs its own
platform run. Existing nonfatal build warnings (optional font CSS, stale
Browserslist data, mixed imports and bundle size) remain. Rendering was tested
in Chromium with the real desktop page; a packaged Electron installation,
live channel connections and production services were not exercised.

The [integrated release contract](../orchestration-release-001/README.md),
including restricted execution, native-only verification, pre-fix journal
inspection and controlled deployment/rollback requirements, remains in force.
Only the known renderer type gate is closed by this change. Master integration
uses fast-forward ancestry so its product tree is the tested tree.
