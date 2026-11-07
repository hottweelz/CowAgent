# Phase 4: title requests only

1. Confirm the selected OpenRouter Nemotron endpoint supports `reasoning` and
   `max_tokens`, and that reasoning is optional. Use official documentation and
   public endpoint/model metadata; do not change provider routing or config.
2. Apply `reasoning.enabled=false` and a 128-token output limit only to primary
   title calls on that verified model/endpoint, using a copy of the bot's args.
   Keep the title prompt, all other providers, the configured fallback chain,
   and local title fallback unchanged. Reject output truncated by a token limit.
3. Test the serialized title request, unchanged ordinary requests/shared state,
   unsupported providers, title quality boundaries, usage and both fallbacks.
4. Run one bounded before/after live comparison on synthetic English and Chinese
   conversations through the real title path in an isolated data directory.
   Compare raw provider input/output/reasoning counters with normalized receipts.
   Retain only counts, hashes and quality checks; never publish prompts or keys.
5. One independent bounded review, documentation and handoff, then commit/push
   the existing tracked branch and verify zero divergence. No dynamic discovery,
   primary model change, production database operation, merge or deployment.

Team: Codex lead implements and verifies; one Luna/high worker maps title paths
and writes focused tests; a second Luna/high worker performs one read-only
review. No changes to instruction or identity files.
