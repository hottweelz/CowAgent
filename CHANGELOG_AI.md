# AI handoff ledger

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
