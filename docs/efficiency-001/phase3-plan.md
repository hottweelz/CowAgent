# Phase 3: cache-prefix stability only

Scope: preserve instruction text, tool schemas, all 16 tools and capabilities.
No model, provider routing, cache directive, identity, instruction-file, title
budget or ChannelsPage change. Use private workspace/database copies only.

1. Lead: move the two dated memory-guidance lines into the final runtime block
   in `agent/prompt/builder.py`; put stable runtime metadata before date text.
   Keep current dates live and preserve prompt/accounting invalidation.
2. Luna worker: sort skill entries only when formatting their prompt. Preserve
   discovery/override precedence, filtering and every instruction/skill entry.
3. Lead and worker: add focused tests for deterministic builds, locale/project
   paths, date rollover, unchanged instruction-line content, skills in different
   insertion orders, tool/schema equality and request freshness. Run existing
   prompt/accounting/skill tests affected by those paths.
4. Lead: measure frozen before/after prompts on a fresh private runtime copy.
   Compare full-template token counts and common prefixes across a controlled
   date change, retaining only counts/hashes. Make a bounded Nemotron sequence
   for each version: first lookup, indexed-memory continuation, identical repeat,
   and date-only variation. Keep all 16 schemas and request options unchanged.
   Record actual model/provider, timings and raw numeric cache usage. First
   requests are not assumed cold; cache reuse is observed, never guaranteed.
5. One bounded independent review; fix concrete findings. Document evidence,
   limitations and preservation checks, update the handoff, commit and push the
   tracked branch, then fetch and verify zero divergence. No merge/deployment.

Acceptance: identical unchanged-input builds; every original instruction line
retained; date variation changes only the intended suffix; no stale date or
schema/routing change; successful indexed retrieval with all tools; raw provider
cache counters retained and compared. Report observed cache reuse separately
from the local prefix estimates.
