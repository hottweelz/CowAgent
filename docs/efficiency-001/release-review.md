# Consolidated release review: SQLite and Phases 1–4

Reviewed 2026-11-06 America/New_York. Optimization stops after Phase 4; dynamic
tool discovery and further architecture changes remain deferred.

The verified code was fast-forwarded from the fork's `master` at `19e84350`
to `8eef97dc`. Its tree is identical to the reviewed optimization branch:
`b479ffd25382bdada656cf906a86ab94d5a1c6b9`. This consolidation adds documentation
only. The existing audit and SQLite branches remain available; no branch was
deleted, history rewritten, binary release published or runtime restarted.

Release decision: approved for the authorized fork merge, with the explicitly
accepted renderer typecheck baseline below. No new blocking failure or
actionable review finding was found.

## Included work

| Area | Result and limits |
|---|---|
| [SQLite fix](../memory-sqlite-io.md) | Precise operation/path/SQLite-code/traceback diagnostics; I/O errors propagate without disabling WAL/FTS. The durable host repair keeps active databases outside the pCloud-backed Projects directory. Code alone does not relocate another installation. |
| [Phase 1](phase1.md) | Account for actual request shape, selected tool schemas and context budget; distinguish latest request, current estimate, run totals and auxiliary title attempts. Missing counters remain unknown. |
| [Phase 2](phase2.md) | Shorter prose for four tools; all 16 tools and argument schemas retained. Matched live first input saved 199 tokens (2.0%). |
| [Phase 3](phase3.md) | Stable prompt/skill ordering preserves instructions and live dates. A longer date-rollover prefix did not produce extra provider cache reuse in the measured sequence. |
| [Phase 4](phase4.md) | Verified Nemotron title-only reasoning/output controls. Paired English/Chinese title output fell 792 -> 10 tokens; reasoning 775 -> 0. Four synthetic calls do not establish universal quality or latency gains. |

## Integrated regression

The [verification receipt](release-verification.json) records the exact 85-file
Python selection, revisions, counts and preservation checks.

| Gate | Result |
|---|---|
| Integrated Python selection | 867 passed, 15 skipped in 16.20 seconds. |
| Opt-in native browser subset | All 7 previously skipped native Chrome cases passed using private profiles. Combined unique result: **874 passed, 8 Windows-only skips**. |
| Web/desktop usage labels | **8 Node tests passed**; changed web JavaScript syntax checks passed. |
| Desktop production build | Passed renderer bundling and main-process TypeScript compilation. |
| Strict renderer typecheck | **FAILED: 9 pre-existing ChannelsPage TS2322 errors**, exit 2. Baseline and reviewed-branch diagnostics are identical with the same dependencies. |
| Python static checks | F-class Ruff passed; all 34 changed Python files compiled. |
| Independent integrated review | One Sol 6.1/high review; no actionable must-fix findings. |
| Post-merge core smoke | **61 passed** across storage I/O, shared DB recovery, FTS, request accounting, usage and title budget. These repeat a subset of the 874; do not add them as unique cases. |

The eight remaining skips are two Windows path-separator cases and six native
PowerShell cases. Native Windows execution was not available on this macOS host.
The existing optional-web module stub requires collecting `test_openai_chat_api`
before `test_session_context_usage`; the recorded selection preserves that order.

The renderer issue is tracked separately in
[ChannelsPage typecheck baseline](../known-issues/channels-page-typecheck.md).
The passing bundle build is not treated as a passing renderer typecheck. Existing
build warnings about optional font CSS, browser compatibility data, mixed
sessionStore imports and bundle size remain outside this merge.

## SQLite, persistence and request integration

A new private workspace copy used SQLite's read-only online backup sources for
both canonical databases. No production DB was deleted, overwritten or rebuilt.
Hashes of config plus 33 active workspace files matched before and after the
copy and three fresh-process checks.

Each fresh process called the normal TestPilot `_setup_memory_system`, registered
`memory_search` and `memory_get`, and returned the same retained indexed result.
SQL trace confirmed FTS `MATCH`; LIKE fallback was blocked. WAL, Unicode FTS5,
trigram FTS5 and `integrity_check=ok` passed in all three processes. Snapshot
history row hashes remained identical: 11 sessions, 33 messages and 14 runs.
The source workspace remains at `CowAgent-Runtime/workspace`, outside the
previously identified Projects backup root. The historical pCloud rename was
not syscall-traced; its attribution and evidence limits remain in the SQLite report.

The existing offline replay then built the real prompt and serialized both
requests on this fresh copy: all 16 tools remained present; the two requests had
identical system/tool blocks; the retained memory lookup executed FTS successfully.
No new provider calls were made for this consolidation. Earlier live Phase 2–4
receipts remain valid evidence for their stated scope; they were not relabeled
as a new live end-to-end run.

## Reproduction and remaining limits

Use a private `COW_DATA_DIR`. The receipt's `python_test_files` list is the
integrated pytest selection; enable `COW_BROWSER_NATIVE_TEST=1` for the seven
browser cases. Also run `node --test tests/test_usage_display.mjs`, desktop
`npm run build`, and the separately recorded strict renderer check.

Private logs, JUnit results, fresh DB copy and memory smoke runner are retained
under `/private/tmp/cowagent-release-rmkpu4fm`; frontend/base comparisons are
under `/private/tmp/cowagent-frontend-checks.gJt5tJ`. No raw private prompts,
responses, database rows or credentials are committed in the receipt.

This was a scoped integrated regression, not every repository test or a packaged
desktop release. Production restart, a fresh full UI/provider conversation,
remote embeddings and native Windows execution were not performed. Source and
test evidence cover the merged code; existing live measurements retain their
sample-size and provider-variability limits. The checkout/PID path still lies
inside Projects, so its prior conflict-file risk is separate from the relocated
memory databases. Existing untracked AGENTS.md and conflict PID files are retained.

Next work is a separate ChannelsPage baseline repair if requested. No further
token optimization or dynamic tool discovery is authorized by this consolidation.
