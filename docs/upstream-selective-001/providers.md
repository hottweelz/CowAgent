# Provider patch port

## Upstream sources

- Gemini: commit `6ca21f1268f1185bc3b43cf6d3258ed243622a37`, authored by
  c020627 on 2026-11-07. It adds a 180-second guard for REST SSE comment-only
  streams and yields an empty chunk for each comment so callers can observe
  cancellation.
- LinkAI: commit `f6e824f9d30a0ffead3704846dbf270609146af3`, authored by
  c020627 on 2026-11-10. It trims history repeatedly until the configured
  character budget fits, while preserving the system prompt and newest turn.

## Changes

Gemini now tracks elapsed inactivity with `time.monotonic()`. SSE comment lines
yield `{}` and return a retryable 504 after more than 180 seconds without a
non-empty, non-comment line. This leaves the existing 900-second read timeout,
SDK streaming path, JSON parsing fallback, and ordinary chunk handling intact.

LinkAI now repeatedly removes stale history while preserving message zero and
the newest user turn. It removes older turns (including intermediate tool-role
messages) together. For histories with no user message, it removes the oldest
non-system message until the budget fits. If only the current user turn remains,
it is kept whole even when over budget, including trailing tool results.

## Verification

Using the existing project Python 3.13 environment and the prepared cache:

- `TIKTOKEN_CACHE_DIR=/private/tmp/cow-infra-tiktoken-cache '/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python' scripts/ci_test.py -q tests/test_gemini_stream_keepalive.py tests/test_linkai_session_history_trim.py` — 21 passed.
- Ruff F-gate on the two provider modules and two focused tests — passed.
- `py_compile` on those same four files — passed.
- `git diff --check` — passed.

Both upstream regression test files were retained verbatim as the base, then
extended. Gemini retains all seven upstream cases and adds malformed-data clock
reset and a 240-second first-data delay case. LinkAI retains all ten upstream
cases and adds current-user preservation after an orphan assistant message and
preservation of a current turn with a trailing tool result. No provider calls
or live-service access were used.
