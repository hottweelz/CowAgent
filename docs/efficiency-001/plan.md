# EFFICIENCY-001 audit plan

Scope: establish a baseline and propose optimizations. Do not change production
behavior, credentials, instructions, tools, identities, or active database records.

1. Read the current config and take isolated workspace/database snapshots using
   read-only SQLite backup sources. Record source revision and safe metadata.
2. Trace prompt construction, adapter serialization, local estimates, provider
   usage, caching metadata, and separate title requests. Pin current behavior
   with synthetic tests in `tests/test_efficiency_*_baseline.py`.
3. Add `scripts/efficiency_metrics.py` and `scripts/benchmark_context_cache.py`.
   Measure the actual prompt builder and tool schema outputs on the snapshot.
   Record only lengths, token estimates, hashes, usage counters, model IDs,
   timings, status, and aggregate results. Never save prompts or credentials.
4. Reconstruct the recorded two-call memory lookup from retained message blocks.
   Compare its persisted provider totals with local estimates and component
   contributions. Clearly label token proxies and inferred per-call counts.
5. Compare the active and recently used OpenRouter models, as selected by the
   maintainer. Keep all tool schemas and prompt instructions. Execute only the
   requested indexed-memory read in the isolated snapshot. Measure identical
   request repeats and report raw provider cache counters, including missing
   fields. Measure title generation separately.
6. Publish sanitized JSON evidence and an audit report under
   `docs/efficiency-001/`, including a request diagram, component/tool breakdown,
   caching findings, ranked opportunities, estimated savings, and an actionable
   implementation/regression plan for review. Update the handoff and commit the
   audit branch without merging or applying optimizations.

Acceptance: all eight investigation requirements are mapped to inspected source
or measured evidence; provider counts are distinct from estimates; the active
database is never opened for writing; metrics tests and bounded mocked-adapter
tests pass. Missing metadata is reported as unknown, never as a confirmed cache hit.
