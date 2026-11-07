# ChannelsPage renderer typecheck baseline

Status: **resolved and verified on 2026-11-07 America/New_York** in
`9604bde7cacd19aeb914b345dcc5c9ea8616e0e4`. The local icon alias now uses
`React.JSXElementConstructor<{ size?: number }>` so it checks the JSX call
contract instead of incompatible React.FC static prop validators. Strict
renderer typecheck now exits zero, with strictness and dependencies unchanged.
Real channel-icon rendering and the full release gates passed; see the
[fix and evidence](../channel-icon-typecheck/README.md).

The following is the preserved **failed historical baseline**, verified
2026-11-06. It was accepted separately for the Phases 1–4 merge, then remained
a blocker for ORCHESTRATION-RELEASE-001 until this focused correction.

```bash
cd desktop
npx tsc --noEmit -p tsconfig.json
```

Exit code: **2**. Exactly **9 TS2322 errors** in
`desktop/src/renderer/src/pages/ChannelsPage.tsx`, at:

| Line | Column |
|---:|---:|
| 57 | 13 |
| 59 | 15 |
| 60 | 16 |
| 61 | 9 |
| 62 | 20 |
| 63 | 16 |
| 64 | 15 |
| 66 | 12 |
| 67 | 14 |

Each reported a Lucide `ForwardRefExoticComponent` that was not assignable to
`IconComponent`. The nested size-validator types disagree because Lucide permits
a string size as well as a number. That earlier merge included no correction.

The source at the fork's pre-merge `master`, commit `19e84350`, was extracted to
a private directory and checked with the same installed dependency tree as
`8eef97dc`. Both strict checks produce byte-identical normalized diagnostics
(SHA-256 `bf985076359ae7d3974afdbfbdb64738a8a881111d1ace69ff4a81c49f92d297`).
The reviewed branch does not change `ChannelsPage.tsx`.

`npm run build` passes the renderer bundle and main-process TypeScript build.
That command does not prove that the renderer's strict typecheck passes.
Do not replace or hide the failing strict check with the successful build.

The separate follow-up is complete. The type fix changes no channel runtime
JavaScript, model settings or channel behavior. Retain strict renderer typecheck
as a required gate; do not replace it with the successful bundle build.
