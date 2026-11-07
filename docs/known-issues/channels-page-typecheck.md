# ChannelsPage renderer typecheck baseline

Status: **open, pre-existing, accepted separately for the Phases 1–4 merge**.
Verified 2026-11-06 America/New_York. This is a failed check, not a passing gate.
It is outside the authorized SQLite/context optimization scope.

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

Each reports a Lucide `ForwardRefExoticComponent` that is not assignable to
`IconComponent`. The nested size-validator types disagree because Lucide permits
a string size as well as a number. No correction is included in this merge.

The source at the fork's pre-merge `master`, commit `19e84350`, was extracted to
a private directory and checked with the same installed dependency tree as
`8eef97dc`. Both strict checks produce byte-identical normalized diagnostics
(SHA-256 `bf985076359ae7d3974afdbfbdb64738a8a881111d1ace69ff4a81c49f92d297`).
The reviewed branch does not change `ChannelsPage.tsx`.

`npm run build` passes the renderer bundle and main-process TypeScript build.
That command does not prove that the renderer's strict typecheck passes.
Do not replace or hide the failing strict check with the successful build.

Separate follow-up: reconcile `IconComponent` with the installed Lucide icon
types, then require the strict renderer check to exit zero and verify channel
icon rendering. Keep this defect separate from future optimization proposals.
