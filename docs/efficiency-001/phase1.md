# Phase 1: accurate request accounting and context budgeting

Implemented on `audit/efficiency-001-context-cache`, following audit commit
`4792f8f5`. The maintainer authorized implementation and publication of this
branch. At this commit, Phases 2–5 remained proposals; this change does not shorten instructions,
remove tools, change model selection or add cache-routing directives.

Follow-up: the [live accounting gate and Phase 2](phase2.md) are now complete.
That report records fresh provider/UI evidence and the additional latest-request
display. The verification and limits below describe the original Phase 1 commit.

## Result

The executor now captures counts and hashes from the assembled `LLMRequest` after
message preparation and tool selection. Diagnostics and the context chart use
this snapshot. The local estimate includes system, injected schemas and history.
It remains a character heuristic, not a provider tokenizer or an exact billable
count. No prompt bodies are retained in the accounting snapshot.

The isolated audit replay kept both first and second request hashes identical to
the saved baseline. All 16 tools remain available and the retained memory query
still executed FTS `MATCH` successfully. No provider calls were made in Phase 1.

| First request | Before | Phase 1 |
|---|---:|---:|
| Diagnostic input estimate | 4,553 | 9,220 |
| System estimate | 4,506 | 4,506 |
| Injected schema estimate | omitted | 4,667 |
| History estimate | 47 | 47 |
| Saved provider input count | 9,960 | same historical measurement |

The residual 740-token gap is estimator/template error. Phase 1 does not claim
token savings. The frozen native-template estimate of 9,961 and actual provider
measurements remain in [baseline.json](baseline.json).

## Accounting contract

- `request_accounting` contains model, purpose, component estimates and exact
  fingerprints for system, schemas and messages at the LLMRequest boundary.
- The context chart uses provider input only when the current request matches the
  saved fingerprints and the provider actually reported input usage. A model,
  tool, prompt, permission, relevant file-state or history change invalidates
  that reuse. Equal-length edits are still changes. Hovering does not rebuild
  the prompt. File changes that need a rebuild mark saved estimates stale.
- `breakdown_estimated` remains true even when the total is actual. The chart
  exposes its latest request separately; appending the answer normally makes
  the current context an estimate again. Saved session snapshots remain marked
  as restored by the existing API. The system slice includes its embedded skill
  catalog; the tools slice counts injected schemas and is labeled "Tools".
- Input budgeting reserves system plus selected schemas. Model capacity,
  configured input budget and output reserve are separate fields. An explicit
  catalog completion cap larger than the policy reserve also consumes space.
  Reactive overflow recovery uses the same schema reservation and respects the
  configured cap rather than imposing a 2,000-token minimum above it.
- MCP budget previews do not commit speculative selections. Selection is checked
  against post-trim history; newly loaded schemas are budgeted before the first
  request. An unchanged preview is reused to avoid a duplicate retrieval call.
  Proactive trimming does not remove new tool chains between steps.
- The legacy custom gateway can use an unambiguous saved capacity for a fully
  qualified model ID imported under another catalog bucket. Conflicts use the
  conservative family/default path. This budget-only lookup does not borrow
  completion caps, credentials or routing from another provider. Direct catalog
  metadata takes precedence and fallback routing uses its own catalog bucket.

Usage normalization preserves reported input/output, cache reads/writes, reasoning,
cost, returned model/provider and purpose. `*_reported_calls` records reporting
coverage. Missing metadata remains unknown; explicit zero is retained. The run
sum includes all attempted model calls, with flat, count-only per-request records.
A request with no usage cannot inherit the preceding call's actual totals.

Web and desktop tooltips label unknown and partial usage. A cache percentage is
shown for complete coverage; partial reporting shows a known-token subtotal.
Existing persisted records without coverage fields remain readable. The OpenAI
compatible API omits cache details when coverage is unknown or incomplete.

Title generation exposes `title_attempts` on its existing response, with separate
primary/fallback status and available usage. It does not enter agent run totals.
Bots returning only flat token counters retain those known counters; unavailable
input/cache details are not fabricated. No title model, output budget or reasoning
setting was changed.

## Verification

The count-only [verification receipt](phase1-verification.json) lists the exact
Python test files and before/after replay measurements.

All checks used synthetic data or the private runtime snapshot; active databases,
config, credentials, identities, instructions and memory were not modified.

- **342 focused Python tests passed**, covering request freshness, actual totals,
  unknown/zero/partial metadata, title paths, UI-facing API usage, persistence,
  model catalog lookup, trimming, overflow, tool retrieval, retries/fallbacks,
  steering, incremental persistence and Responses API contracts.
- **6 Node tests passed**, executing the web and desktop usage-label functions.
- `npm ci --ignore-scripts --no-audit --no-fund` used the existing desktop lockfile;
  it changed no manifest or lockfile. `npm run build` passed (renderer and main).
- Python F-class lint, Python compilation, web JavaScript syntax and diff checks
  passed. One independent Terra 6.1 engineering review found callback isolation,
  flat title usage and MCP selection/budget edge cases; each has a focused test
  and fix. No further review chain was used.
- Offline replay: identical first/second payload hashes, 16 schemas, successful
  indexed retrieval, no live calls. The test data remained private.

Reproduce the core checks with a private `COW_DATA_DIR`:

```sh
COW_DATA_DIR=/private/tmp/cowagent-phase1-check .venv/bin/python -m pytest -q \
  tests/test_request_accounting.py tests/test_request_usage.py \
  tests/test_efficiency_accounting_baseline.py tests/test_efficiency_adapter_baseline.py \
  tests/test_message_usage.py tests/test_agent_trim_budget.py tests/test_token_budget_trim.py
node --test tests/test_usage_display.mjs
cd desktop
npm run build
```

Run `tests/test_openai_chat_api.py` separately or before
`tests/test_session_context_usage.py`. The latter's existing module-level stub can
replace `web` during collection if it is loaded first. The final 342-case run
loaded the real web API tests first and passed. This test-order issue was not
expanded into an unrelated fixture rewrite.

## Limits

A separate `tsc --noEmit -p tsconfig.json` reports nine `ChannelsPage.tsx` icon-type
errors. The same nine errors were reproduced from unmodified `4792f8f5` using the
same locked dependencies in a private directory. No changed file has a reported
type error. Vite's production build and the main-process TypeScript build pass.
Existing font-asset, chunk-size and browser-data build warnings remain.

No live web/desktop interaction or new provider generation was performed. Native
tokenizer calibration and later optimization phases are outside this change.
Unknown provider completion defaults can still exceed the reserve; existing
reactive recovery remains necessary. A single oversized current turn is retained
by the existing policy rather than silently dropping its content. Retries hidden
inside a bot's plain title wrapper cannot be itemized when that wrapper returns
no metadata. Title attempt receipts are returned by the API, not added to a new
persistent database ledger.
