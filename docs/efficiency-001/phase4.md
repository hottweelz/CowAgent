# Phase 4: title-only reasoning and output budget

The selected Nemotron model spent most title output tokens on reasoning. Its
normal title path had no reasoning control or output cap. The change adds
`reasoning: {enabled: false}` and `max_tokens: 128` only to primary title requests
for `nvidia/nemotron-3.5-super-vl:free` at `https://openrouter.ai/api/v1`.

The ordinary agent request path, model, sampling settings, tool schemas and
cache behavior are unchanged. The primary title prompt is unchanged. The policy
copies the bot's arguments; it never mutates the shared bot or configuration.
Other models/providers, Responses calls and the configured fallback chain keep
their previous options. This is a deliberately verified route, not a universal
reasoning policy. Dynamic tool discovery is outside this phase.

## Provider support

Checked on 2026-11-07 UTC. The [OpenRouter model page](https://openrouter.ai/nvidia/nemotron-3.5-super-vl:free)
states that reasoning defaults on and can be disabled. The public
[model catalog](https://openrouter.ai/api/v1/models) reports
`reasoning.mandatory=false`. The [endpoint metadata](https://openrouter.ai/api/v1/models/nvidia/nemotron-3.5-super-vl:free/endpoints)
lists the Nvidia endpoint and support for `reasoning` and `max_tokens`.

OpenRouter's [reasoning documentation](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)
describes the request-local reasoning controls. On Chat Completions, the output
cap includes both reasoning and visible output. `exclude=true` only hides
reasoning; it does not save those tokens. Therefore this change disables
reasoning on the verified title route rather than merely excluding its text.
The live zero-reasoning counters below verify that the endpoint honored it.

128 tokens leave headroom for the existing six-word English / fifteen-character
Chinese instruction. A returned `finish_reason=length` now rejects a truncated
primary title and enters the existing fallback chain. Empty/error responses and
invalid titles retain the previous fallback behavior. If the chain also fails,
the existing first-line local title remains. Failed title attempts still retain
their available usage and remain separate from the main agent run.

## Bounded live result

One campaign, four HTTP calls: two public synthetic conversations, each before
and after the change, through `generate_session_title` and the real shared
ChatGPTBot/HTTP adapter. Baseline title service: `b226e895`. Both versions use
the same prompt and configured sampling values; only the two title budget
fields differ. All replies report the selected model and provider `Nvidia`.

| Case | Version | Input | Output including reasoning | Reasoning | Total | Seconds |
|---|---|---:|---:|---:|---:|---:|
| English | Before | 84 | 504 | 496 | 588 | 3.695 |
| English | After | 84 | 4 | 0 | 88 | 0.699 |
| Chinese | Before | 98 | 288 | 279 | 386 | 1.915 |
| Chinese | After | 98 | 6 | 0 | 104 | 0.559 |

Combined output fell 792 -> 10 tokens (98.7%); total input plus output fell
974 -> 192 (80.3%). Reasoning is a subset of output, not an additional charge.
The original 350-token audit title is a historical sample, not the matched
baseline here. All calls report zero cost on this free route, so this measures
token reduction, not money saved. Four calls do not establish latency or title
quality guarantees across workloads.

Both English titles mention the SQLite topic, have no extra lines/thinking text,
and use at most six words (5 before, 3 after). Both Chinese titles mention Tokyo
and fit the fifteen-character limit (7 before, 5 after). All four finished with
`stop`, passed the normal title validation and used one primary attempt without
fallback. The normalized input/output/total/reasoning counters match raw usage.
See the [sanitized receipt](phase4-verification.json) for counts and hashes.

## Verification and preservation

Focused tests cover the actual serialized HTTP request, ordinary calls before
and after a title, shared-argument preservation, route gates, useful English and
Chinese titles, truncated/empty/error titles, configured fallback and local
fallback, and separate usage accounting. Existing adapter/accounting tests stay
in scope. Final commands/results are in the handoff ledger.

The live harness uses an isolated `COW_DATA_DIR`, loads credentials only into
memory and disables application logging before imports. It sends synthetic
conversations only, with a one-request-per-case guard and 60-second HTTP timeout.
It compares the baseline module loaded from Git with the current module, observes
the actual HTTP boundary, and asserts byte-equivalent request dictionaries after
adding only the two intended options. The private runner is retained at
`/private/tmp/cowagent-phase4-live.py`; receipts are in
`/var/folders/nn/3yz7zzyj617029dmpfzcvk940000gn/T/cowagent-phase4-lr1x_ubp`.
Do not rerun live calls just to regenerate bookkeeping.

Hashes of 34 active source files (workspace files including memory/history DBs,
plus config) matched before/after. No production database was opened by SQLite,
copied, rebuilt or edited; no application server was started. No identity or
instruction file changed. UI/desktop and live memory retrieval were not rerun:
this phase has no frontend or primary-agent request change. The Phase 3 indexed
retrieval evidence remains the preceding live memory verification.

Remaining limits: provider support can change; an output-limit failure can still
incur the unchanged fallback cost; other models/routes have no new title budget.
Expanding the policy requires their own support and quality evidence.
