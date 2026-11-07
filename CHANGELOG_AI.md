# AI handoff ledger

## 2026-11-06 22:35 EST — Codex — Phase 4 title budget

- Task: reduce title overhead using supported request-local controls; preserve
  primary agent behavior and fallback; compare provider usage; push the branch.
- Result: four live synthetic requests, two matched before/after pairs. English
  output 504 -> 4 (reasoning 496 -> 0); Chinese 288 -> 6 (279 -> 0). Combined
  output 792 -> 10, total input/output 974 -> 192; input unchanged at 182.
  All report Nvidia/Nemotron, finish_reason=stop and valid topical short titles.
  Cost is zero on this free route; do not claim monetary or general latency gains.
- Team: Codex lead owns provider research, policy, live comparison, integration
  and publication. Luna/high worker maps paths and owns focused tests; a separate
  Luna/high read-only reviewer found no must-fix issues. Requested models accepted;
  effective worker models not independently exposed. Used STE Writing Plans and
  its evidence rule; no HomeBoss. Current tracked audit branch retained.
- Changes: primary titles on the exact verified OpenRouter Nemotron free route
  copy bot args and set reasoning.enabled=false/max_tokens=128. Other routes and
  configured fallback options unchanged. ChatGPTBot retains finish_reason;
  truncated primary titles enter the existing fallback with usage retained.
  No primary-agent request, model, sampling, instruction, tool or routing change.
- Files: `agent/chat/session_service.py`, `models/chatgpt/chat_gpt_bot.py`,
  `tests/test_session_title_budget.py`; efficiency README/implementation plan,
  new phase4 plan/report/sanitized verification JSON; this ledger.
- Commands/tests: private-COW_DATA_DIR `.venv/bin/python -m pytest -q` passed 14
  tests in `test_session_title_budget`, `test_request_usage`,
  `test_efficiency_adapter_baseline`; 73 in `test_efficiency_accounting_baseline`,
  `test_request_accounting`, `test_openai_api_type`, `test_provider_error_body`,
  `test_custom_provider`, `test_responses_failed_status`, `test_responses_refusal`.
  All names are under tests/ with .py. F-class Ruff, py_compile, diff check and
  numeric receipt reconciliation passed. Removed one unused test import found
  by Ruff; no runtime change. Self-review and one independent review complete.
- Live method: real generate_session_title/ChatGPTBot/HTTP path, original
  b226e895 title service compared with current code, identical synthetic inputs
  and configured sampling. Only reasoning/max_tokens differ. Raw counters equal
  normalized receipts; all four use one primary attempt without fallback. Shared
  bot args unchanged. Quality checks cover topic, language length, no extra lines
  or thought tags. No private prompts/responses/credentials in published evidence.
- Decisions: verify official model/endpoint support and live honoring before
  claiming savings; scope the budget to that exact route. Keep unsupported
  providers and fallback budgets intact. Reasoning is included in output totals.
- Lessons Learned:
  - Mistake: treating an auxiliary title like an unrestricted reasoning task, or
    hiding reasoning text and counting that as avoided generation.
  - Root Cause: the title path inherited model defaults without task-specific
    controls; this endpoint enables reasoning by default.
  - Future Trigger: auxiliary request output dominated by reasoning tokens.
  - Required Behavior Change: verify per-route controls, set request-local
    budgets, and preserve usage/fallback when an output limit is reached.
  - Verification Step: unchanged ordinary payload/shared args, complete short
    titles, real raw versus normalized reasoning counts, matched before/after.
  - Durable Memory Update: implementation and support limits are in phase4.md.
- Preservation: hashes of config plus 33 active workspace files including DBs
  unchanged. No production SQLite operations, server restart, identity or
  instruction edits. MEMORY.md update: not needed (no project file); no global
  memory changes. Preserve untracked AGENTS.md and three conflicted PID files.
- Known limits: four live calls cannot establish universal title quality or
  latency gains. Fallback can still cost more; other routes remain unbudgeted.
  Provider support can drift. UI/desktop and live memory retrieval not rerun:
  no frontend/primary request changes; preceding Phase 3 FTS evidence remains.
  Nine existing ChannelsPage type errors stay out of scope.
- Next recommended steps: none for this authorized phase. Dynamic tool discovery
  remains deferred; extending title controls requires route-specific evidence.
- Next-agent notes: see phase4.md/phase4-verification.json. Private runner:
  `/private/tmp/cowagent-phase4-live.py`; private receipts under the temp path
  recorded in phase4.md. Parent commits/pushes tracked origin branch, fetches,
  and requires HEAD...@{u}=0 0. No merge or deployment.

## 2026-11-06 22:19 EST — Codex — Phase 3 prefix stability

- Task: implement only deterministic cache-prefix ordering and measure Nemotron
  reuse. Provider routing/cache-control changes explicitly excluded. Kept the
  tracked `audit/efficiency-001-context-cache` branch; no merge or deployment.
- Result: pinned-template date-rollover common prefix 1,130 -> 4,204 tokens;
  full first request remains 9,776 estimated / 9,775 actual. **No additional
  date-rollover cache reuse observed**: both versions returned cached_tokens=0
  after the date changed. Both continuations and exact repeats returned 8,672.
  Do not describe this as demonstrated cache savings or a latency improvement.
- Team: Codex lead owns builder, comparative runner, integration and publication;
  Luna/high worker maps prompt volatility and owns skill formatter/tests; one
  Luna/high read-only reviewer checks final code and measurement scope. Requested
  models were accepted; effective models not independently exposed. Used STE
  Writing Plans and its evidence rule. No HomeBoss.
- Changes: defer the two exact dated memory-guidance lines to the final runtime
  block; place stable metadata before dates and team/language before runtime.
  Sort available/unavailable skill presentation by name/path without changing
  discovery precedence, filtering or content. Dates remain live and prior usage
  becomes estimated when date freshness changes. No tool or provider code changed.
- Files: `agent/prompt/builder.py`, `agent/skills/formatter.py`,
  `scripts/efficiency_metrics.py`, new `scripts/benchmark_prefix_stability.py`,
  `tests/test_efficiency_metrics.py`, new `tests/test_prompt_prefix_stability.py`
  and `tests/test_skill_prompt_order.py`; efficiency README/implementation plan/
  phase2 link, new phase3 plan/report/verification JSON; this ledger.
- Evidence: fresh private workspace copy with read-only SQLite backup sources.
  Compared original `0ce6dfef` builder/formatter against working code at the same
  date and next date. Every instruction line preserved, all 16 full tool schemas
  identical, user messages/request options identical. No added provider field,
  header, cache directive or title request. Exact-repeat request hashes match.
- Live: eight real requests, four per version (first, indexed continuation,
  identical repeat, date-only variation), all reported model Nemotron and provider
  Nvidia. First/repeat/rollover input 9,775; continuation input 10,010 in both
  versions. First calls returned one indexed FTS result each and no LIKE fallback;
  both continuations answered. Repeat/rollover calls selected memory_search.
  Raw cache fields agree with CowAgent normalization, with reporting coverage.
- Performance limits: after-change continuation took 96.374 s; other calls took
  1.570–2.887 s. Single paired sequence, unknown internal endpoint/cache policy,
  no cold-request or causality assumptions. Public template places tools after
  the system date, so those later tool blocks are outside the stable day prefix.
  No extra campaign was run merely to seek a favorable result.
- Commands/checks: private-COW_DATA_DIR `.venv/bin/python -m pytest -q` passed 77
  tests across `test_prompt_prefix_stability`, `test_skill_prompt_order`,
  `test_time_tool`, `test_request_accounting`, `test_efficiency_accounting_baseline`,
  `test_efficiency_metrics`, `test_efficiency_benchmark`, `test_tool_description_contract`,
  `test_skill_custom_provider_types`, `test_skill_metadata_booleans`,
  `test_skill_list_name_types`, `test_skill_config_entry_shapes`,
  `test_skill_hidden_setup_hints`, `test_skill_loader_cache` (all tests/*.py).
  F-class Ruff, py_compile, diff checks, count-receipt reconciliation and active
  source hash comparison passed. Bounded independent review: no must-fix findings.
- Decisions: retain exact instructions and capabilities; report structural prefix
  improvement separately from empirical cache reuse. Do not add routing hints or
  weaken freshness to obtain a hit. Full web UI/desktop gates are not repeated:
  no frontend changes; existing nine ChannelsPage typecheck errors stay out of scope.
- Lessons Learned:
  - Mistake: interpreting a longer local token prefix as proof of provider cache
    reuse, or checking only the obvious late runtime date for volatility.
  - Root Cause: daily memory filenames break the early prefix; backend cache and
    endpoint behavior are not determined solely by the public chat template.
  - Future Trigger: new dates/runtime values early in prompts, unsorted catalogs,
    or a prefix estimate offered as evidence of billed/cache-hit savings.
  - Required Behavior Change: preserve text while ordering stable inputs first;
    compare real raw cache counters and retain negative results and latency outliers.
  - Verification Step: date-only before/after builds, line-multiset/schema equality,
    live FTS lookup, exact repeats and provider-reported cache reads.
  - Durable Memory Update: implementation and limits are in phase3.md.
- Preservation: production DB/history/config/instruction/identity files unchanged;
  pre-copy source hashes verified. No runtime server started or restarted. Private
  benchmark process completed. Preserve untracked AGENTS.md and three conflict PID
  files. MEMORY.md update: not needed; no project memory file exists and no new
  project governance was adopted. No global memory updates.
- Next recommended steps: none for the authorized implementation. Any provider
  controls/routing experiment needs separate authorization; cache gain is unproven.
- Next-agent notes: `docs/efficiency-001/phase3.md` and its sanitized receipt are
  the result, not a successful caching claim. Private data/receipts are under
  `/private/tmp/cowagent-phase3-9gp54gqd`; never commit the runtime copy. Pinned
  tokenizer/template remain in the earlier audit directory. Parent commits and
  pushes the existing upstream, fetches, and verifies HEAD...@{u} = 0 0.

## 2026-11-06 20:18 EST — Codex — Live accounting gate and Phase 2

- Task: verify live TestPilot/Nemotron accounting with all 16 tools before
  compressing scheduler/browser/search_files/bash descriptions; push the branch.
  The live gate passed before Phase 2 edits. No merge or production deployment.
- Team: Codex lead; Luna/high workers for live-path/count evidence, scope-label UI,
  scheduler/browser prose, and search/bash prose. The evidence worker performed
  one bounded final engineering review. Runtime accepted the requested models;
  effective worker models were not independently exposed. Used STE Playwright
  guidance; browser host was unavailable, so the CLI drove a private Chrome.
- Live gate: normal web chat/Agent pipeline on a private consistent copy of
  existing memory/history, configured Nemotron, 16 tools on both calls. FTS5
  returned one row; no LIKE fallback. Raw input 9,994 + 10,271 = 20,265; output
  83 + 73 = 156. Both raw cache reads were explicitly zero and matched stored
  counters. UI exposed a gap: latest-request data existed only in the API.
- Changes: web/desktop cards now show latest actual input/output separately from
  estimated current context; reply tooltips say Run total. Unknown, partial and
  reported-zero behavior is preserved. Shortened only four tool descriptions
  and Bash's desktop prose variant; parameter schemas and execution logic remain.
- Measured result: identical first-request messages, all 16 argument schemas
  equal; actual first input 9,994 -> 9,795, saving 199 tokens (2.0%). Matched public
  NVIDIA template also saves 199; four target blocks save 7.1%, below the proposed
  20–35% range because parameter prose and safeguards remain. The non-desktop
  replay saves 185; do not mix that variant with the live desktop variant.
- Post-change verification: indexed lookup again returned one FTS row. Latest
  input/output 10,094/42; run 19,889/147. Provider cache read 8,672 was retained
  exactly and the actual UI showed Cached 44% for the run. Previous session usage
  restored after private server restart. Four live auto-selection cases exposed
  all 16 tools; each chose the expected tool with valid args and succeeded on
  isolated fixtures (unsent reminder record, local browser page, search, printf).
- Files: four modules under `agent/tools/{bash,browser,scheduler,search_files}`;
  web `chat/context-usage.js` and `core/i18n.js`; desktop ContextUsagePopover,
  types and i18n; `tests/test_tool_description_contract.py`,
  `tests/test_usage_display.mjs`; efficiency README, phase1, implementation plan,
  new phase2 report/verification JSON; this ledger.
- Commands/checks: private-COW_DATA_DIR pytest groups passed 85 scheduler/browser/
  schema cases (seven real Chrome ref actions), 68 Bash/schema cases, and worker
  130 search/Windows-guidance cases with six optional skips. Four schema cases
  overlap the first two groups; worker repeated eight Windows guidance tests
  after its final edit. Exact groups are recorded below. Eight Node display tests,
  Python compilation/F-class Ruff, web syntax, JSON/diff checks passed. Desktop
  production build passed. Renderer typecheck found a missing tf import in the
  new partial-usage view; fixed it, then only the nine pre-existing ChannelsPage
  icon errors remained. The final desktop build was repeated after that fix.
- Test groups: `test_tool_description_contract`, scheduler `relative_store`,
  `once_past_time`, `timezone`, `silent`, `cross_channel_recipients`,
  `task_permission_mode`; browser `ref_actions_native`, `snapshot_selector`,
  `fill_required_text`, `scroll_amount`, `driver_loss`, plus
  `test_security_ssrf_browser_navigate`; Bash `full_output`, `background`,
  `exit_codes`, `rm_safety_flags`, `config_propagation`; search_files `tool`,
  `brace_globs_native`, `powershell_quoting`, plus `test_bash_windows_guidance`.
  All names are under tests/ with `.py`; Bash and scheduler names have `test_`
  prefixes. Node command: `node --test tests/test_usage_display.mjs`.
- Decisions: keep all parameter descriptions and capabilities; count actual
  request saving separately from generated continuation variability. No cache
  directives, model/identity/instruction changes or title-budget changes. The
  configured credential stayed in memory; global .env bootstrap was skipped in
  the private test server. Optional Playwright 1.64.1/pyee/greenlet were installed
  only in the existing .venv for native browser tests; no manifest/lock changes.
- Lessons Learned:
  - Mistake: API scope separation did not make the latest request visible in the
    UI; a production bundler also did not catch an unimported JSX helper.
  - Root Cause: Phase 1 lacked a real UI gate; Vite transpiles the renderer without
    a full typecheck. Non-desktop versus desktop prose also changes token totals.
  - Future Trigger: usage-scope changes, renderer helper additions, or comparisons
    of descriptions with runtime workspace/platform substitutions.
  - Required Behavior Change: check rendered labels against real provider counts;
    inspect typecheck errors against the known baseline; compare matched variants.
  - Verification Step: real browser assertions, raw/normalized counter agreement,
    scoped schema/AST tests, four live selection/execution cases and desktop build.
  - Durable Memory Update: contract and measured limits recorded in phase2.md.
- Known issues: single memory case/four synthetic selections are not broad quality
  coverage; provider cache reuse is variable. Native Windows shell and desktop GUI
  were not exercised. Existing renderer icon errors remain out of scope. The web
  client logged expected connection refusals during the private restart; no new
  uncaught JS error. No claim of a production restart or exact provider template.
- Preservation: source memory/history/instruction file hashes match the pre-copy
  manifest; no production DB/config rewrite. Both private server and private
  browser were stopped. Preserve unrelated untracked AGENTS.md and three
  conflicted PID files. No global memory changes. MEMORY.md update: not needed;
  no project memory file exists and instruction files are outside this scope.
- Next recommended steps: none for this deliverable. Phases 3–5 stay proposals.
- Next-agent notes: report `docs/efficiency-001/phase2.md`; sanitized numeric JSON
  beside it. Private receipts, UI captures and one-off reproduction scripts are
  under `/private/tmp/cowagent-live-phase1-88lj2ns1`; never commit that runtime copy.
  Working branch tracks `origin/audit/efficiency-001-context-cache`; parent commits
  intended files, pushes, fetches and requires HEAD...@{u} = 0 0. No merge.

## 2026-11-06 19:29 EST — Codex — EFFICIENCY-001 Phase 1 accounting

- Task: implement the approved Phase 1 request accounting/context budgeting and
  push `audit/efficiency-001-context-cache` to the matching branch on `origin`.
  The maintainer's explicit push instruction authorizes establishing its upstream.
  No merge, deployment, model selection change or Phase 2–5 optimization.
- Team: Codex lead owns snapshots, context/budget integration, tests and Git;
  Terra 6.1/high worker owns provider/title usage because these paths interact
  across adapters and APIs; Luna/high worker maps and updates usage consumers;
  one Terra 6.1/high read-only reviewer checks snapshot lifecycle and budget
  invariants across modules. These integration assignments exceeded routine Luna
  lookup work. Runtime accepted explicit models; effective models not independently
  exposed. Continued the STE Writing Plans guidance. No HomeBoss.
- Changes: shared count-only LLMRequest snapshot; system/tool/history/model
  fingerprints; current estimates versus latest actual request; schema-aware
  proactive/overflow budgets, configured cap and known completion reserve;
  budget-only imported catalog capacity lookup for unambiguous qualified custom
  models. Existing request output parameters and capabilities stay intact.
- Usage: retain cache reads/writes, reasoning, cost, returned model/provider and
  purpose. Aggregate known counters with reported-call coverage and per-attempt
  records, including unknown attempts. Web/desktop distinguish unknown, partial
  and reported zero; slices remain labeled estimated. Title primary/fallback
  attempts are separate API receipts, including flat-counter bots. No DB migration.
- Files: `agent/protocol/{accounting.py,usage.py,agent.py,agent_stream.py}`;
  `bridge/agent_bridge.py`; `agent/chat/session_service.py`; OpenAI-compatible,
  ChatGPT and Responses adapters; web session/OpenAI APIs and usage/i18n JS;
  desktop usage components/types/i18n; benchmark runner; focused accounting,
  usage, API and Node tests; `docs/efficiency-001/phase1.md`, verification JSON,
  implementation-plan status and this ledger. Exact files are in the commit diff.
- Checks: 342 focused Python cases passed across the 30 files listed in
  `phase1-verification.json`, with the web API test collected before the existing
  session-context module stub. Six Node usage-label tests passed. F-class Ruff,
  `py_compile`, web JS syntax and diff checks passed. `npm ci --ignore-scripts
  --no-audit --no-fund` installed existing locked desktop dependencies without
  changing manifests/lockfile; `npm run build` passed renderer and main builds.
- Replay: existing private snapshot, no new provider calls. Both request hashes
  match the audit baseline; 16 schemas retained; indexed FTS MATCH succeeds.
  First diagnostic estimate changes from 4,553 to 9,220 (system 4,506 + schemas
  4,667 + history 47), versus historical actual 9,960. Remaining difference is
  explicitly local estimator/template error, not token savings.
- Review fixes: callbacks cannot replace a fresh prompt or abort a request;
  flat title counts are retained; speculative MCP selection is not committed,
  post-trim selection is checked and newly synced schemas consume budget before
  the first request. Regression tests cover each. Standalone retry executors
  retain an independent usage ledger even without an Agent object.
- Lessons Learned:
  - Mistake: measuring a cached prompt/schema-free budget, treating missing
    counters as zero, or letting observability change prompt construction.
  - Root Cause: separate accounting sources and reporting scopes; callbacks and
    MCP selection can change between preview, trimming and the actual request.
  - Future Trigger: context data changes without history growth, partial usage,
    callback failure, newly loaded tools or a routed/fallback model change.
  - Required Behavior Change: count the final request; validate freshness with
    hashes; retain reporting coverage; keep accounting failures off the request
    behavior path; commit MCP selection only for the actual post-trim request.
  - Verification Step: synthetic executor/adapter/API tests, no-usage/fallback
    cases, post-trim selection tests, snapshot replay and unchanged payload hashes.
  - Durable Memory Update: implemented contract is in `docs/efficiency-001/phase1.md`.
- Known limits: the strict desktop renderer typecheck has nine ChannelsPage icon
  type errors, reproduced unchanged at audit commit `4792f8f5`; changed files have
  no reported type errors and the production build passes. Existing build warnings
  and test module-stub ordering are documented. No live UI or fresh provider
  generation was run. Estimates remain heuristic; unknown provider output defaults
  and a single oversized current turn retain existing reactive recovery. Bot-internal
  title retries without returned metadata cannot be itemized. Title receipts are
  returned, not added to a new persistent ledger.
- Preservation: no active database/config/credential/instruction/identity changes.
  Tests use isolated temporary data and the prior private snapshot. Preserve
  untracked AGENTS.md and three conflict PID files. No global memory updates.
- MEMORY.md update: not needed; no project memory file exists, and the implemented
  contract is documented beside the audit without changing instruction files.
- Next recommended steps: review Phase 1 on the pushed branch; authorize Phase 2
  separately if tool-description changes are wanted. Do not merge automatically.
- Next-agent notes: private test/replay evidence and baseline typecheck are under
  `/private/tmp/cowagent-accounting-phase1-4pEX47`; no private runtime snapshot is
  committed. Git publication targets `origin/audit/efficiency-001-context-cache`;
  completion requires a post-push fetch and `HEAD...@{u}` count of `0 0`.

## 2026-11-06 19:03 EST — Codex — EFFICIENCY-001 baseline audit

- Task: trace and measure context construction, token accounting, cache metadata,
  indexed-memory requests and separate title calls; propose changes for review.
  Audit only. No optimization, production source/config change or merge.
- Branch: `audit/efficiency-001-context-cache`, created with no upstream from
  `37d947bb`. Scope is independent of the completed SQLite repair below.
- Team: Codex lead; Luna/high workers for prompt/component metrics, adapter/cache
  inspection and tests, and token-accounting inspection and tests; one Luna/high
  read-only reviewer for audit code and report evidence. Model selections were
  accepted by the runtime; effective worker models were not independently exposed.
  Used the STE Writing Plans skill and performance-engineer guidance. No HomeBoss.
- Findings: the diagnostic estimate omits schemas; the chart reads a cached
  initialization prompt that differs from the prompt sent; provider input is per
  call while the assistant footer sums calls. The public NVIDIA template counted
  9,961 tokens versus 9,960 actual first-request input. Its tool blocks account for
  5,457 estimated tokens (54.8%). Component counts remain local estimates.
- Live results: Nemotron's two-call indexed-memory task used 20,155 input / 119
  output tokens; the continuation and exact first-request repeat each reported
  8,672 cached input tokens. Title generation separately used 91 input / 259 output
  (252 reasoning). `openrouter/free` completed the task but changed underlying
  models/providers and reported zero cached tokens. Gemma returned HTTP 429 on
  all six attempts across two bounded campaigns. Total requests: 14; all eight
  successful responses reported cost 0. No invented Gemma token/latency metrics.
- Preservation: both SQLite sources opened read-only/query-only for backup;
  both source main-file hashes unchanged during snapshot. All CowAgent maintenance
  and tool execution used the private clone. No active runtime database writes,
  identity/instruction edits, capability removal or credential changes. Published
  artifacts contain counts, hashes, numeric usage, routing and timing only.
- Files: `scripts/benchmark_context_cache.py`, `scripts/efficiency_metrics.py`,
  `scripts/requirements-efficiency-audit.txt`, four `tests/test_efficiency_*.py`
  files, `docs/efficiency-001/{README.md,baseline.json,plan.md,reproduce.md,
  implementation-plan.md}`, and this ledger. Optional audit dependencies were
  installed only in the existing `.venv`; production requirements were unchanged.
- Checks: `COW_DATA_DIR=<private audit path> .venv/bin/python -m pytest -q` with
  the four audit test files passed 12 tests. F-class Ruff checks, `py_compile` and
  `git diff --check` passed. Final offline runner with the pinned NVIDIA tokenizer
  and template preserved the live baseline's first-request hash, counted 9,961,
  retained 16 tools and executed FTS MATCH successfully. No new provider call was
  needed for that verification. Artifact credential/private-body scan and relative
  document links passed. Self-review and bounded independent review were performed.
- Decisions: compare active/recent OpenRouter models as selected by maintainer;
  keep raw actual usage separate from local proxy/template estimates; record
  missing metadata as unknown in evidence; do not interpret response caching as
  prompt caching. Rank accounting correctness before schema or prefix changes.
- Lessons Learned:
  - Mistake: comparing a schema-free estimate or cached prompt with total provider
    input, or treating a normalized zero cache field as conclusive provider evidence.
  - Root Cause: accounting uses different prompt snapshots and aggregation scopes;
    raw JSON does not match provider chat-template serialization; metadata is lost.
  - Future Trigger: large estimate/provider gaps, 0% cache displays, unexpected
    title usage, or a router-model comparison with inconsistent input counts.
  - Required Behavior Change: fingerprint the sent request; retain raw numeric
    cache provenance; separate latest call, run sum and auxiliary request usage.
  - Verification Step: compare count-only actual adapter payloads, pinned local
    template estimates and raw provider counters; verify indexed reads on a clone.
  - Durable Memory Update: findings and the proposed contract are in the audit
    report and implementation plan, not in user instruction files.
- Known limits: original full wire requests and exact first-campaign UTC request
  timestamps were not retained; current reconstruction is labeled. Public NVIDIA
  deployment/template identity is unconfirmed despite the one-token agreement.
  Repeat followed a continuation, so the sequence is not an isolated cache-causality
  experiment. No successful Gemma baseline, long-history/multimodal/MCP benchmark,
  web UI replay or title-fallback cost measurement. These limits are explicit.
- MEMORY.md update: not needed; no project memory file existed and no new project
  governance or architecture decision was adopted. Global memory was not changed.
- Next recommended steps: review `docs/efficiency-001/implementation-plan.md`;
  authorize a bounded accounting phase before optimizations. Measure Gemma when
  its endpoint is available if successful-generation comparison is still needed.
- Next-agent notes: private snapshot and intermediate receipts remain at
  `/private/tmp/cowagent-efficiency-001-fqoww935`; they contain private runtime data
  and must not be committed. Preserve the unrelated untracked `AGENTS.md` and
  three `.cow [conflicted...].pid` files. The runtime remains outside pCloud backup
  at CowAgent-Runtime; do not revert its path to CowAgent-TestData/workspace.
- GitHub sync blocked: GitHub remote exists but current branch has no tracked upstream.
  Intended audit work is committed locally. No upstream is guessed or set, and no
  merge or push is performed.

## 2026-11-06 17:42 EST — Codex — SQLite memory I/O repair

- Task: investigate and fix TestPilot's recurring indexed-memory startup failure.
- Branch: `fix/memory-sqlite-io`, created from the current `master` checkout.
- Team: Codex lead; Luna/high workers for conflict provenance, memory-path/test
  inspection and regression tests; one Luna/high read-only engineering review.
  The runtime accepted these model selections; effective worker model was not
  independently exposed. No HomeBoss or external worker pool used.
- Cause: live SQLite WAL files inside pCloud's active `Projects` backup were
  renamed as conflict copies. Two conflict WAL timestamps match the logged
  failures. A controlled WAL rename reproduced `SQLITE_IOERR_SHORT_READ` (522)
  at `PRAGMA journal_mode=WAL`. The historical syscall was not traced; the UI
  backup mapping, timestamp correlation, healthy isolated copies, and exact
  reproduction support the attribution. Fresh DBs worked on both APFS disks.
- Source changes: precise operation/path/SQLite-code/name/traceback diagnostics;
  full initialization error boundary and connection cleanup; propagate trigram
  I/O and cleanup errors instead of disabling indexing. WAL remains enabled.
- Host repair: copied all 29 workspace files to the previously nonexistent
  `/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace`, outside the active
  backup roots. SHA-256 checks verified the copy. Changed only `agent_workspace`
  and the matching `web_file_serve_root` in CowAgent-TestData/config.json.
  Original config and manifests are retained in CowAgent-Runtime. All original
  databases, conflicted companions, memory, history, identities and instructions
  remain intact. No production database was deleted, overwritten, or rebuilt.
- Repository files: `agent/memory/storage.py`,
  `tests/test_memory_storage_io.py`, `docs/memory-sqlite-io.md`, this ledger.
- Checks: project `.venv` Python 3.13.1 / SQLite 3.45.3; installed pytest and ruff
  only in that existing environment. `pytest -q tests/test_shared_db_recovery.py
  tests/test_memory_fts_sync.py` passed 24 tests. The worker's combined run with
  the initial new test file passed 36 tests. After adding one cleanup-error test
  and stricter operation assertions, `pytest -q tests/test_memory_storage_io.py`
  passed all 13 tests: 37 distinct focused cases passed on the final behavior.
  Test logs were routed outside production. `ruff check` on both changed Python
  files with `--select F --ignore F403,F405`, `py_compile`, and `git diff --check`
  passed. Self-review and one independent review found no blocking defect.
- Runtime results: three fresh processes called TestPilot's normal
  `_setup_memory_system` using the active config. Each registered `memory_search`
  and `memory_get`; `memory_search` returned the retained indexed row with LIKE
  fallback blocked. WAL, both FTS indexes, and integrity checks passed. Separate
  storage reopen checks passed. Complete persisted rows matched snapshots,
  including all 10 sessions, 29 messages, and 13 runs in the shared DB. All 29
  original file hashes and copied non-database file hashes remained unchanged.
- Decisions: fix the external file lifecycle through a verified runtime copy;
  do not disable WAL, delete sidecars, merge conflict WALs, or rebuild databases.
  The root pCloud backup and unrelated projects were not changed. Do not add an
  exclusion and assume it protects files already included in that backup.
- Known limits: full chat/server startup and remote embedding-provider behavior
  were not exercised. The application was stopped at entry and remains stopped;
  the actual memory setup/tool path was executed directly in fresh processes.
  No model calls were made. A short synthetic workload in the backed-up folder
  did not reproduce the intermittent pCloud event itself; deterministic WAL
  rename did. Open-connection failures can produce a precise diagnostic plus a
  second outer initialization diagnostic. The code checkout/PID location is
  still under backup; that separate operational risk was not expanded here.
- Lessons Learned:
  - Mistake: treating a healthy main database as proof that live WAL use is safe.
  - Root Cause: external conflict renames break SQLite's companion-file lifecycle;
    the old initialization message hid the exact failing operation.
  - Future Trigger: `[conflicted]` DB/WAL/SHM/PID names or recurring I/O after recovery.
  - Required Behavior Change: inspect backup coverage and record extended SQLite
    diagnostics before changing journaling, rebuilding, or moving existing data.
  - Verification Step: use an isolated WAL-rename reproduction, then verify real
    indexed retrieval across new processes and compare all retained history rows.
  - Durable Memory Update: operational findings are in `docs/memory-sqlite-io.md`.
- MEMORY.md update: not needed; no project memory file existed, and no new project
  instruction or architecture policy was introduced. Instruction files were not changed.
- Next recommended steps: run the usual CowAgent start command with the existing
  CowAgent-TestData `COW_DATA_DIR`; retain the new workspace path. Establish
  off-device backups from consistent SQLite backup artifacts. Do not revert to
  the old workspace after the new copy receives writes. Assign an upstream only
  with maintainer direction if GitHub publication is wanted.
- Next-agent notes: private receipts are in
  `CowAgent-Runtime/diagnostics/2026-11-06-memory-io/`. The original workspace is
  preserved, not an active second copy. Initial untracked `.cow [conflicted].pid`,
  `.cow [conflicted 2].pid`, and `AGENTS.md` are unrelated and must remain unstaged.
- GitHub sync blocked: GitHub remote exists but current branch has no tracked upstream.
  Intended changes are committed locally; no upstream was guessed or set.
