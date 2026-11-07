# Phase 3: deterministic cache prefixes

Implemented only the authorized prefix-ordering work. No provider routing,
cache-control fields, model selection, tool schema, capability, identity or user
instruction file changed. The [numeric receipt](phase3-verification.json) records
the before/after comparison against `0ce6dfef`.

**Result:** the estimated common prefix across a date change grows from **1,130
to 4,204 tokens**. Every original instruction line remains and the full request
size is unchanged. **The live test did not show additional cache reuse across
the date change:** both versions reported zero cached tokens on that request.
Unchanged requests still produced provider-confirmed cache hits.

## What changed

`agent/prompt/builder.py` previously put today's daily-memory filename twice
inside the early memory section. A new day changed those lines before most of
the workspace and context instructions. The later runtime date also preceded
runtime metadata, team instructions and the response-language rule.

The builder now defers the two exact dated memory lines to its final runtime
block. Team and response-language text come before that block; stable runtime
metadata comes before the date. All existing wording is retained, including
project-mode absolute memory paths. Dates are rebuilt on each request; accounting
still invalidates old provider totals when the date or other prompt inputs change.
No clock value is added to the prompt. The time tool remains available.

Skill discovery used filesystem/manager insertion order for prompt presentation.
`agent/skills/formatter.py` now sorts available and unavailable entries by name
and file path. This changes presentation order only. Discovery precedence,
filtering, disabled-skill behavior, descriptions and setup hints remain intact.
Tool order already had a deterministic presentation path and was not changed.

## Frozen comparison

The benchmark uses a fresh private copy of TestPilot's existing workspace and
consistent SQLite backups from read-only sources. It builds both source versions
with the same tools, context files, model, request options and controlled date.
It then advances the date inside prompt building only. The machine clock and
production files are unchanged. Before and after instruction-line multisets are
exactly equal for each date; only order changes. All 16 complete schemas and
non-system messages are equal.

| Pinned NVIDIA template estimate | Before | After |
|---|---:|---:|
| Full first request | 9,776 | 9,776 |
| Tool blocks | 5,272 | 5,272 |
| Common prefix across date rollover | 1,130 | 4,204 |

This is a **3,074-token longer common prefix**, not a token-count saving. The
public template is a local proxy; the provider's exact deployment template is
unconfirmed. In that template, tool definitions follow the system message, so
they still fall after the date difference. The change protects more system
instructions but cannot preserve those later tool blocks across a date change.
Other real changes to context, skills or the team can still change the prefix.

## Provider measurement

Eight bounded requests used the configured
`nvidia/nemotron-3.5-super-vl:free` model. Every response reported provider `Nvidia`.
The sequence for each version was first lookup, indexed-memory continuation,
identical first-request repeat, then date-only variation. No routing hint,
session key, cache directive, title request or automatic retry was added.
First requests are not assumed cold.

| Request | Input, both versions | Cached before | Cached after |
|---|---:|---:|---:|
| First lookup | 9,775 | 0 | 0 |
| Indexed-memory continuation | 10,010 | 8,672 | 8,672 |
| Identical first-request repeat | 9,775 | 8,672 | 8,672 |
| Date-only variation | 9,775 | 0 | 0 |

Both first lookups executed real FTS `MATCH`, returned one indexed result and
used no LIKE fallback. Both continuations produced a final answer. Repeats and
date variants selected `memory_search`. All requests retained all **16 tools**.

Raw `prompt_tokens_details.cached_tokens` and `cache_write_tokens` were retained
and compared with CowAgent's usage normalization. Missing values are not treated
as observed zero; here all eight responses explicitly reported the counters.
Their meaning follows [OpenRouter's cache usage documentation](https://openrouter.ai/docs/guides/best-practices/prompt-caching#usage-object-fields).

The longer partial prefix did not produce a reported cache hit in this campaign.
The provider's internal cache policy and endpoint identity are not observable
from these responses, so the result does not identify why. No threshold, routing
or future savings claim is inferred. The after-change continuation took 96.374
seconds; the other requests took 1.570–2.887 seconds. This single sequence does
not support a latency improvement claim. No extra calls were made to seek a more
favorable outcome.

## Verification and limits

- **77 focused Python tests passed.** New cases cover unchanged-input builds,
  `en`/`zh`/`zh-Hant` language inputs, project/default paths,
  missing runtime/memory tools, date rollover, preserved dated guidance and
  historical user text, and invalidation of prior actual usage. Skill cases
  cover reversed insertion order, path tie-breaking, disabled entries and setup
  hints. Existing accounting, time, metrics, memory/tool schema and related skill
  tests passed.
- All original instruction lines, full tool schemas and request options were
  compared at runtime against the baseline. Actual request hashes prove each
  repeat was identical to its first request. Provider counters reconcile with
  normalized values and indicate cache-field reporting coverage on every call.
- Python compilation, F-class Ruff checks and `git diff --check` passed. One
  bounded independent Luna review found no must-fix finding.
- Active workspace file hashes match the pre-copy manifest. No production
  database, history, config, identity or instruction file was rewritten. No
  runtime restart, merge or deployment was performed.
- This phase exercises the real prompt builder, adapter, provider and memory
  search on a private copy. It does not repeat the prior web UI gate. No frontend
  source changed; the nine existing `ChannelsPage.tsx` typecheck errors remain
  outside scope.

The measured benefit is deterministic ordering and a longer unchanged prefix.
Additional provider cache savings remain **unproven**. Provider controls and
routing experiments remain separately unapproved work.

## Reproduction

Use a consistent private workspace copy and a read-only config source. The
runner validates that the copy is separate from active runtime paths and rejects
symlinks/MCP configurations. Logs and output contain counts/hashes only. The
baseline is loaded from local Git; no network code is executed.

```sh
COW_DATA_DIR=/private/tmp/cowagent-phase3-check .venv/bin/python -m pytest -q \
  tests/test_prompt_prefix_stability.py tests/test_skill_prompt_order.py \
  tests/test_time_tool.py tests/test_request_accounting.py tests/test_efficiency_metrics.py

.venv/bin/python scripts/benchmark_prefix_stability.py \
  --config /path/to/config.json --snapshot /private/path/workspace \
  --output /private/path/phase3.json --baseline 0ce6dfef \
  --tokenizer-json /path/to/pinned/tokenizer.json \
  --chat-template /path/to/pinned/chat_template.jinja
```

Add `--live` only to repeat the eight real provider calls. The pinned artifact
hashes are recorded in the receipt. No raw prompts, responses or credentials are
written to the report. The handoff names this run's private evidence directory.
