# EFFICIENCY-001 proposed implementation plan

Status: **Phases 1 and 2 implemented; Phases 3–5 remain for review**. See the
[Phase 1 result](phase1.md) and [live gate and Phase 2 verification](phase2.md).
The [baseline](README.md) and
[numeric receipts](baseline.json) are the decision inputs. Keep model selection,
identities, user instruction files, memory, skills and all tool capabilities.
Do not write to active runtime databases during implementation tests.

## 1. Make accounting describe the request actually sent

Work in `agent/protocol/agent.py`, `agent/protocol/agent_stream.py`,
`models/openai_compatible_bot.py`, the HTTP usage boundary and title service.

- Capture a count-only accounting snapshot when the executor finishes prompt,
  messages and tool selection. Use the same snapshot for diagnostics, context
  budgeting and the UI. Do not rebuild prompts just to draw the chart.
- Include actual injected schemas in input estimates and compaction budgeting.
  Keep model capacity, configured budget and output reserve distinct.
- Fingerprint prompt, tools and model alongside history. Invalidate a past
  provider total when the request changes; do not rely only on 15% history drift.
- Keep latest-request input, multi-call run totals and auxiliary title calls as
  separate fields. Label component slices as estimated even when their sum is
  scaled to an actual provider total.
- Preserve whether cache metadata was present. Distinguish unknown from zero.
  Retain numeric cache reads/writes, reasoning, cost, actual model/provider and
  request purpose without storing prompt bodies or credentials.
- Use saved model metadata when available and retain a safe unknown-model
  fallback. Do not silently raise the user's token budget.

Acceptance tests: rebuilt prompt differs from cached initialization prompt;
tools change without history changing; selected model changes; schema tokens
consume context budget; actual per-call 9,967 + 10,241 remains run input 20,208;
missing cache fields remain unknown; reported zero remains zero; title usage is
separate. Update the audit characterization tests only when the new contract is
implemented. Test streaming and non-streaming usage with synthetic responses.

Expected token saving: **zero**. This step makes savings and overflow prevention
testable. It must not modify the request content or capabilities merely to make
the displayed number smaller.

## 2. Reduce oversized tool-description prose

Start with scheduler, browser, search_files and bash: 2,805 of the 5,457 estimated
tool-template tokens. Review their implementations and existing argument tests
before editing descriptions. Consolidate repeated examples and prose while
preserving names, parameter names, types, required fields, enum values, defaults,
permission rules, warnings and error recovery instructions.

Acceptance tests: structural schema comparison; existing tests for these four
tools; representative tool-selection and valid-argument tasks in an isolated
workspace; the indexed-memory task still completes with all 16 tools exposed.
Measure full-template and actual provider counts before/after. The review target
is a 20–35% reduction in these four blocks, **561–982 tokens per request**; it is
a scenario, not a promised result. Reject edits that reduce task correctness.

## 3. Preserve stable prefixes and expose supported cache controls

Keep stable instruction wording/order deterministic. Move date-dependent daily
memory filenames into the existing volatile suffix while keeping their meaning
and current date available. Do not freeze runtime dates or stale file contents.
Check whether tool/skill ordering is already stable before changing it.

Add a provider-specific, explicit allowlist for supported routing/cache fields
through the custom adapter. Use an opaque session identifier rather than prompt
text or private user names. Do not forward arbitrary kwargs, activate whole-response
caching, or pin a provider by default. Confirm current field support from
[OpenRouter documentation](https://openrouter.ai/docs/guides/best-practices/prompt-caching)
when implementing. The current Nemotron path already showed cache hits without
these fields, so no universal improvement is assumed.

Acceptance tests: two same-input builds stay identical; a date change alters
only the intended suffix and still updates all date guidance; all original
instruction content survives; supported fields reach HTTP and unsupported fields
do not. Use one controlled first/continuation/repeat sequence per available
selected model. Record raw cache counters, actual provider/model and timestamps.
Do not call a first request cold unless the provider guarantees it. Run a second
bounded sequence only if needed to resolve a concrete variance. Treat HTTP 429
as unavailable and honor `Retry-After`; do not retry in a tight loop.

Expected reduction in input tokens: **zero**. Cache reuse and latency may improve;
the amount depends on route, TTL, provider implementation and workload. Dollar
savings cannot be inferred from the current free-model sample.

## 4. Bound and account for title generation

Preserve title generation as a separate task. First expose its usage and fallback
attempts. Then test a supported title-specific reasoning/output budget with the
same selected model. Do not globally lower reasoning or change agent model
selection. A deterministic local title is a separate product decision, not part
of this plan's authorized implementation.

Acceptance tests: one normal title request; primary failure and one configured
fallback; no double counting in assistant run totals; usable, bounded titles;
no change to memory task output. Compare actual usage with the measured
91-input/259-output baseline. The **0–252 output-token** saving range is only a
scenario based on the reported reasoning tokens; provider support and quality
determine the result.

## 5. Consider further reductions only after the measured changes

Consolidating application-authored tool-use guidance may remove an estimated
163–326 tokens per request if 10–20% of the measured relevant sections proves
redundant. Review instruction equivalence before testing. Do not edit AGENT.md,
USER.md, RULE.md or MEMORY.md under this audit's authorization.

Built-in tool discovery is a separate, higher-risk experiment. It could avoid
some of the 5,050 tokens attributed to the 14 non-memory tool blocks on this
memory task, but discovery overhead, added calls, cache loss and task mistakes
reduce that ceiling. It is not authorized here. Every existing tool must remain
reachable, and tests must include initial requests needing each deferred tool,
multi-tool tasks and recovery from a missed discovery. Skills already load their
full instructions on demand; do not rebuild that mechanism without evidence.

## Review and release gate

Implement one bounded phase at a time after maintainer review. Retain this audit
branch/evidence as the baseline. Use snapshot-only tests, one focused engineering
review of the final change, and a before/after receipt with the same selected
models and full capabilities. Keep token reduction, cache reuse, task success and
latency as separate outcomes. Do not add overlapping savings scenarios together.

Do not merge, deploy, move runtime paths or alter active databases as part of this
proposal. Gemma successful generation/cache behavior remains to be measured when
that endpoint is available; the completed audit records its current unavailability.
