# AI handoff ledger

## 2026-11-07 14:38 EST — Codex — ORCHESTRATION-RELEASE-001 integrated assessment

- Task/result: consolidated ISOLATION, RECOVERY and VERIFICATION on dedicated
  release/orchestration-release-001. Decision RELEASE BLOCKED solely by the
  required strict renderer gate: nine pre-existing ChannelsPage TS2322 errors.
  Master remains c2c39a2e. No merge, deployment or production restart.
- Team: Codex lead owns scope, persistence test, integration, documentation and
  Git. Luna/high handled native contracts and UI/build gates. Terra 6.1/high
  handled combined process tests and the two review fixes; interacting process,
  identity and durable state required more than routine Luna edits. One Sol
  6.1/high reviewer assessed cross-component authority/data integrity, then
  checked only the two demonstrated corrections. Models were requested as
  stated; effective model identity is not independently exposed. STE planning
  guidance used; no HomeBoss, external pools or recursive review.
- Ancestry/publication: fetched and confirmed master plus the three feature
  branches at 0/0; read all published milestone guides through GitHub and
  matched their blobs. Created branch from origin/master and fast-forwarded
  the linear audit -> isolation -> recovery -> verification -> tracking chain.
  Review fixes are commit 0710e8fc0d40935f5b8aabc6b1b9042b6a7d37cb. Published
  same-name origin branch under the standing maintainer push authorization.
  Final evidence commit follows the same upstream; verify 0/0 after push.
- Changes: preserve guest execution principal/model separately from host
  transcript/task ownership; recheck host project, permission and roster.
  Add transactional retry-generation migration and fenced waiter claims/stops.
  Atomic stopped-row snapshots retain accurate old-attempt outcomes across
  retry; a lost stop CAS retains completed outcomes. Existing task rows remain.
- Tests/evidence: real SIGKILL at five dispatch/effect/completion boundaries;
  safe restart, acknowledged uncertain effects, no completed replay, cancellation
  and timeout provenance, grant revocation, wrong/missing artifacts, concurrent
  claims, sibling denial, independent verification. Persistent profile and file
  hashes plus exact history rows survive; both existing indexes return FTS MATCH
  results without resync/LIKE fallback. Memory/task WAL and integrity pass.
  All 16 historical native schemas, 17 registry and two memory descriptors,
  restricted class allowlist and optional roots/verification fields checked.
- Commands/results: `.venv/bin/python docs/orchestration-release-001/run_regression.py`
  passed 1,364, skipped 15, zero failures/errors across 119 files (40.26s).
  Exact seven skipped native-browser IDs passed separately in fresh profiles;
  unique total 1,371 passed, eight Windows-only skips. Node UI 39 passed;
  desktop build passed with existing warnings. Strict renderer tsc failed exit2
  with byte-matching nine-error baseline. F-class Ruff/compilation of 54 Python
  files and diff checks passed. Focused/reviewer repeats are not added to totals.
- Review: P1 guest-to-host recovery identity drift and P2 stale waiter cancelling
  a new retry reproduced, fixed and regression-tested. Narrow independent fix
  check: seven passed; both findings closed. Prior early-return receipt fix also
  confirmed. Full review/fix details and limitations are in the release report.
- Files: recovery runtime/store, subagent runner, AgentBridge, five new test
  suites, process fixture, reused isolated runner, release docs/receipts,
  MEMORY.md and this ledger.
- Decisions: keep restricted native broker scope. Do not add hard OS isolation,
  remote verifiers/authority, features, model changes or further optimization.
  Native browser proof uses installed Chrome and local file fixtures; no live
  model calls, production profiles, journals, memory or history were accessed.
- Lessons Learned:
  - Mistake: treating transcript owner as execution principal and letting a
    waiting caller issue unfenced task-level stops across retries.
  - Root Cause: distinct identity and execution-generation boundaries were
    conflated at durable replay and polling interfaces.
  - Future Trigger: shared-conversation workers or delayed callbacks/waiters
    that survive an explicit task retry.
  - Required Behavior Change: retain owner/principal separately, validate host
    grants, fence every asynchronous mutation to its observed generation and
    preserve the committed outcome when a cancellation loses its race.
  - Verification Step: guest recovery/model/roster tests, deterministic retry
    and completion interleavings, seeded existing-row migration and full suite.
  - Durable Memory Update: project MEMORY.md records these identity/fencing rules.
- Known issues: nine renderer type errors remain open and block this release.
  Eight Windows-only cases are not verified on macOS; Linux needs its own run.
  Pre-fix guest envelopes already frozen as host cannot be reliably identified
  or repaired automatically; inspect prior pending work before deployment.
  Native checks certify only declared, time-bound filesystem state. Four
  unrelated untracked files remain: AGENTS.md and three conflicted PID files.
- Next recommended steps: fix ChannelsPage icon typing in a separate task;
  rerun strict renderer and channel-icon checks, then request owner-approved
  merge. Inspect pre-fix pending tasks before any authorized deployment.
- Notes for next agent: release report is docs/orchestration-release-001/README.md.
  Evidence includes exact branch ancestry, source hashes, all skip IDs and
  deduplicated counts. Keep production unchanged and preserve the SQLite repair.

## 2026-11-07 14:06 EST — Codex — Publish task branches and retain push preference

- Task: publish the completed recovery and verification commits for tracking;
  retain the maintainer's instruction to push future completed task commits.
- Team: Codex lead only; bounded Git/documentation work needs no delegation.
- Changes/files: published feat/recovery-001-durable-tasks at 8ed52509 and
  feat/verification-001-task-outcomes at 88151dff to the existing origin fork,
  hottweelz/CowAgent; established matching upstreams. Updated project MEMORY.md
  with the standing same-name branch publication preference; added this handoff.
- Commands/results: `git push --atomic --set-upstream origin` for both named
  branches succeeded; `git fetch origin --prune` and ahead/behind comparisons
  returned 0 0 for each. `git diff --check` passed. This documentation commit
  follows the current branch's tracked origin. No behavior changed, so accepted
  regression evidence was retained without rerunning tests.
- Decisions: future completed CowAgent task commits are pushed for tracking.
  New task branches use the same name on the known origin fork. This maintainer
  instruction overrides the default no-upstream stop. Verify sync after pushes;
  merges and deployments retain separate task-specific authorization.
- Lessons Learned: none.
- Known issues: existing nine ChannelsPage type errors remain the separate
  baseline. Unrelated untracked AGENTS.md and three conflicted PID files remain.
- Next recommended steps: none for this publication task.
- Notes for the next agent: both feature branches now track origin. Project
  MEMORY.md was updated with the durable workflow preference. Production data,
  services, model selection and identity files were untouched.

## 2026-11-07 13:16 EST — Codex — VERIFICATION-001 separate task outcomes

- Task/result: separated worker execution, acceptance criteria and independent
  state confirmation. User selected native file/artifact checks first; remote
  service verifiers remain future work. Branch feat/verification-001-task-outcomes
  builds on RECOVERY-001 8ed52509. No merge, deployment or production restart.
- Team: Codex lead owns contract/checker, runtime/service/CLI, tool results,
  gateway failure receipts, process tests, integration, docs and Git. Terra
  6.1/high owned additive report storage and attempt/contract fences; interacting
  durable transitions needed more than routine Luna edits. Luna/high mapped
  result paths, added native integration tests and ran private regression.
  One Sol 6.1/high reviewer examined consequential false-verification paths
  across execution, evidence and authority. Requested models accepted; effective
  models are not independently exposed. Used STE Brainstorming/Writing Plans
  guidance; no HomeBoss or external worker pool.
- Changes: frozen caller verification contract; native file_exists/text_equals/
  json_equals/sha256 checks through the restricted text broker; independent
  read observations with hashes, timestamps and reason codes. Additive report
  table retains history and fences task/attempt/contract identities. Missing or
  unsupported checks remain unverified. Failed mutations/permission refusals
  cannot be hidden by worker prose or a matching pre-existing artifact.
- Results/UI: execution_status, acceptance_status and external_state_status are
  explicit in durable worker results, displays and operator CLI. verified is
  true only for completed/passed/confirmed under the supplied criteria. Failed
  checks return a tool error while execution remains completed and non-replayable.
  CLI verify performs read-only re-observation. Startup finishes a missing report
  after committed execution without another worker attempt or side effect.
- Files: recovery verification/store/runtime/service/CLI; permission gateway;
  AgentStream failure result boundary; subagent runner/tool; agent_delegate;
  recovery process fixture; four new verification suites; two updated assertions
  in the existing isolation delegation suite; docs/verification-001 plan, guide,
  review, runner and evidence; MEMORY.md and CHANGELOG_AI.md.
- Commands/results: `.venv/bin/python docs/verification-001/run_regression.py`
  exited 0: 1,343 passed, 15 skipped, zero failures/errors in 30.95 seconds across
  114 files. Includes 23 verification cases plus all retained SQLite, EFFICIENCY,
  ISOLATION and RECOVERY cases. Seven skips require installed-browser opt-in;
  eight are Windows-only (two path and six PowerShell). F-class Ruff,
  compilation of 17 changed Python files and diff checks passed. Test HOME/data
  were private; only owned HTTP fixture ports were permitted.
- Evidence: correct and wrong native worker artifacts; actual denied, empty,
  malformed and invalid-content Write calls; direct private Read denial; missing,
  unsupported and inaccessible checks; verification-store failure without replay;
  persistent report history and stale-attempt/hash fences. Actual SIGKILL after
  execution commit leaves completed/no-report; fresh service confirms native
  state with attempt_count still 1 and exactly one write. Repeated restart does
  not duplicate verification or execution. No live model provider was used.
- Review: one P1 defect class fixed. Early streamed tool refusals/argument errors
  bypassed the gateway receipt recorder and could falsely accept a matching old
  file. The common stream result boundary now records failures; the gateway
  preserves denial metadata; duplicate blocking receipts are avoided. Lead
  verified fixes with real native paths. No second broad review or independent
  final approval claimed. See docs/verification-001/review.md.
- Test corrections: patching config.conf during a first bridge import captured
  a fixture lambda; patch config.config instead so later model-routing tests
  remain independent. First full run had one old assertion expecting tool
  success after denied Write. Updated it and the private-Read denial assertion
  to require completed execution but failed acceptance, retaining file/privacy
  checks. Product denial-metadata fixes then warranted the final full rerun.
- Decisions: native filesystem observation is the supported external-state
  scope; remote services stay unverified. Criteria are explicit, not inferred
  semantic proof of every goal. Confirmation is time-bound; separate files are
  not an atomic snapshot. No executable validators, provider changes or new
  permission grants. Existing indexed-memory/WAL behavior stays intact.
- Lessons Learned:
  - Mistake: treating tool gateway receipts as complete evidence of every failed
    tool call, although the stream can reject calls before reaching that gateway.
  - Root Cause: execution has several early-return paths; matching artifacts do
    not prove that a requested mutation succeeded.
  - Future Trigger: a new rejection, parsing or retry-protection path, or a new
    verifier consuming tool outcome evidence.
  - Required Behavior Change: record attempt-scoped failed mutations/refusals at
    the common stream boundary and retain denial metadata in gateway receipts.
  - Verification Step: real denied/malformed/empty Write with a matching old file
    must show completed execution, failed acceptance and independently confirmed
    state; a hidden private read remains denied and cannot pass acceptance.
  - Durable Memory Update: project MEMORY.md records the three outcomes, frozen
    criteria and native-only verification limits. No global or production memory
    text was changed.
- Known limits/not verified: remote-service confirmation, binary/rich artifacts,
  semantic/model grading, Windows recovery and production rollout. Trusted-host
  and POSIX boundaries remain; no OS sandbox or exactly-once guarantee. The nine
  ChannelsPage TS2322 errors remain a separate open baseline; no renderer
  typecheck pass is claimed. No identity/instruction/config files changed.
- Next recommended steps: review/merge the dedicated branch, then schedule a
  controlled restart and exercise an operator-owned artifact contract. Define
  an authoritative read API and evidence freshness rules before adding any
  external-service verifier. Publish destination requires maintainer direction.
- Next-agent notes: docs/verification-001/verification.json records final source
  hashes, selected tests and private evidence paths. Preserve untracked AGENTS.md
  and three conflicted PID files. Production databases/history/services were
  untouched; previous phase receipts remain historical evidence for their commits.
- GitHub sync blocked: GitHub remote exists but current branch has no tracked
  upstream. No destination guessed or upstream set. Intended work is committed
  locally; unrelated untracked files are documented above.

## 2026-11-07 12:29 EST — Codex — RECOVERY-001 durable task state and interruption recovery

- Task/result: implemented durable native temporary-worker and local-delegation
  recovery on feat/recovery-001-durable-tasks, based on published ISOLATION
  5b0bb0be. User selected safe automatic recovery and explicit retry when an
  effect may already have happened. No merge, deployment or production restart.
- Team: Codex lead owns integration, tool receipts, startup/CLI, process tests,
  review fixes, evidence and Git. Two Terra 6.1/high workers owned transactional
  storage/locks and runtime restoration; interacting crash/authority boundaries
  required more than routine Luna work. Luna/high mapped paths, migrated bounded
  fixtures, wrote operator docs and ran regression. One Sol 6.1/high independent
  reviewer checked consequential cross-process data integrity. Requested models
  accepted; effective models are not independently exposed. Used STE Writing
  Plans guidance; no HomeBoss or external worker pool.
- Changes: separate private WAL/FULL journal under shared memory/recovery;
  immutable task envelopes, attempt records and pre/post tool receipts; task
  ownership and receiver/session flock; attempt-fenced results, stops and effects.
  Startup consumer recovers abandoned safe attempts from frozen input. Mutating
  intent requires operator review and acknowledged retry. Completed tasks never
  replay. CLI supports list/show/cancel/retry. Restricted views recheck current
  registry, settings, grants and routing without loading private peer history.
- Files: agent/recovery/{store,runtime,service,__main__,__init__}.py;
  agent/permission/{authority,policy}.py; subagent runner; agent_delegate;
  bridge/agent_bridge.py; five migrated tests, four recovery suites and process
  fixture; docs/recovery-001 plan/guide/review/verification/runner; MEMORY.md;
  CHANGELOG_AI.md. No identity, instruction, model configuration or memory-index
  implementation file changed.
- Verification: `.venv/bin/python docs/recovery-001/run_regression.py` exited 0:
  1,320 passed, 15 skipped, zero failures/errors in 29.63 seconds across 110
  files. Includes 26 recovery cases and retained SQLite, EFFICIENCY and ISOLATION
  cases. Seven skips require installed browser opt-in; eight are Windows-only
  (two path separator and six PowerShell). F-class Ruff, compilation of 21
  changed Python files and diff checks passed. Private HOME/data, owned HTTP
  fixture ports only; subprocess model fixtures prohibit network.
- Process evidence: actual SIGKILL before a write automatically recovers in a
  new service process; death after committed intent or after native Write holds
  needs_review. Acknowledged retry keeps prior receipts. Another restart does
  not replay completion. Public SubagentTool records real Write/outcome/task ID;
  journal admission failure starts no model. Real local delegation plus active
  recovery consumer cannot overlap a timed-out worker still closing.
- Review: fixed both independent P1 findings: startup consumer bypass of the
  process-local relay lock; restored default-agent profile pins overriding
  normal global routing. Lead also fixed disabled-subagent recovery, receipt
  failure allowing later effects, and delayed timeout callbacks affecting a
  new attempt. Exact reproductions and regressions are in review.md. No second
  broad review or independent final approval claimed.
- Test corrections: legacy fixtures now provide actual registered identities,
  strict session/project state and private journals; durable admission is not
  mocked away. A concurrency test initially read a stale imported store helper;
  checking its binding proved the wrong private journal was queried. The first
  broad run was incomplete because spawned processes re-entered the unguarded
  regression wrapper. Added a main guard and reran the complete selection;
  only the successful second run is counted.
- Decisions: conservative whole-attempt replay, no exactly-once effect claim;
  current grants can narrow frozen authority. Keep live journals/lock files
  outside file-sync conflict handlers, as with the existing SQLite repair.
  Task-scoped operator cancellation remains available; delayed runtime stops
  are attempt-scoped. Existing configured models/fallback rules remain intact.
- Lessons Learned:
  - Mistake: task ownership alone did not serialize different tasks using the
    same receiver/session, and a task-only timeout could outlive its attempt.
  - Root Cause: process-local locking and unscoped callbacks assumed one caller
    and one attempt, while startup recovery adds independent consumers.
  - Future Trigger: another task consumer, retry transition or asynchronous stop.
  - Required Behavior Change: acquire shared-resource locks in the common claim
    path and carry attempt identity in every delayed runtime stop.
  - Verification Step: separate-process lock contention, active consumer during
    timeout cleanup, and captured old timer invoked against queued/running retry.
  - Durable Memory Update: project MEMORY.md records journal, fencing, recovery
    policy and operating limits. No global or production memory text modified.
- Known limits/not verified: POSIX local-filesystem recovery only; no arbitrary
  program sandbox, remote protocol, chat/scheduler continuation, model-token
  checkpoints or exactly-once effects. Provider cancellation is cooperative;
  a blocked live worker keeps its lock. Live providers and production deployment
  were not exercised. Existing nine ChannelsPage TS2322 errors remain a separate
  open baseline; renderer typecheck was not rerun or claimed passing.
- Next recommended steps: review/merge this dedicated branch, then schedule a
  controlled service restart and inspect the operator queue. Authorize the new
  branch's publish destination if GitHub publication is wanted. Keep dynamic
  tool discovery and other architectural optimization out of this change.
- Next-agent notes: docs/recovery-001/verification.json contains selected tests,
  source/evidence hashes and retained private evidence paths. Production memory,
  history, databases, config and runtime were untouched. Preserve unrelated
  untracked AGENTS.md and the three conflicted PID files.
- GitHub sync blocked: GitHub remote exists but current branch has no tracked
  upstream. No destination was guessed and no upstream was set. Intended work
  is committed locally; unrelated untracked files remain documented above.

## 2026-11-07 11:08 EST — Codex — ISOLATION-001 restricted worker authority

- Task: implement and validate enforceable worker authority from the attached
  ISOLATION-001 brief. Baseline master c2c39a2e, audit docs 06e0a4dd. Dedicated
  branch fix/isolation-001-worker-authority; no merge or deployment.
- Result: verified fail-closed restricted mode, the brief's permitted fallback.
  Arbitrary untrusted execution and OS worker isolation remain unsupported.
  Native text-file operations, time and bounded local file/text delegation work.
- Team: Codex lead owns filesystem broker, macOS/baseline probes, integration,
  evidence and Git. Luna/high mapped entry paths and migrated subagent fixtures.
  Sol 6.1/high assessed interacting authority/credential boundaries; two Terra
  6.1/high workers implemented cross-module authorization and delegation.
  One separate Sol 6.1/high reviewer checked data/security boundaries beyond
  routine Luna review. Requested models accepted; effective models are not
  independently exposed. Used STE security-threat-model guidance; no HomeBoss.
- Changes: immutable capability/root grants; exact-class descriptors; deny
  unknown tools, missing/invalid authority and evaluation errors; gateway for
  stream/wrapper/post-process paths. Legacy scheduled tool calls deny before
  construction. Strict session/project/roster reads prevent stale authority.
  POSIX descriptor-relative text broker rejects symlinks, hard links, private
  state and host-source writes. Case/Unicode aliases cannot bypass exclusions.
  Fresh temporary directories and optional explicit shared roots replace
  implicit parent-resource sharing. Fresh local receiver retains configured
  model and target runtime identity, with caller/receiver exclusions combined.
  Worker MCP hot reload, parent memory/skills/context and mode-only remote
  invocation are disabled by explicit authorization errors.
- Files: agent/permission/{authority,filesystem,policy,__init__}.py; protocol
  Agent/AgentStream; subagent runner/templates/tool; agent_delegate; multiagent
  inbound; scheduler integration; BaseTool; workspace project/session stores;
  bridge/agent_bridge.py; six migrated existing test files and three isolation
  suites; docs/isolation-001 evidence/report/scripts; project MEMORY.md; ledger.
- Baseline: detached disposable c2c39a2e checkout reproduced Bash/Python writing
  a fictional outside marker and copied memory tool reading fictional parent
  state. Native outside/read-only Write stayed denied. No production data used.
- macOS: sandbox-exec exists but Apple marks it deprecated. A narrow prototype
  aborted legitimate interpreter startup; a broad-read prototype denied outside
  writes but exposed a fictional sibling secret. Detached child survived group
  cleanup; the exact fixture child was then killed and verified stopped. No
  experimental profile shipped; no privileged host change or dependency added.
- Commands/results: `.venv/bin/python docs/isolation-001/run_regression.py`:
  1,294 passed, 15 skipped, zero failures/errors over 106 files. Seven skips are
  opt-in native browser tests, eight Windows-specific. Forty focused isolation
  tests are included, not additive. Final target-identity check repeated 41
  delegation/timeout tests, all passed. F-class Ruff, 27-file compilation and
  diff checks passed. Private HOME/COW_DATA_DIR; only owned local HTTP fixture
  ports permitted. First broad-run failures were permissive legacy fixtures and
  a too-strict guard blocking the embedding fixture; no storage fix was needed.
- Indexed-memory verification: real MemoryManager/MemorySearchTool gateway,
  three reopen cycles, FTS MATCH each time, no LIKE fallback, WAL and integrity
  confirmed. SQLite/EFFICIENCY regressions remain included. No production
  TestPilot database, memory/history, identity, skill, instruction or config
  was opened, migrated, deleted or rebuilt. Root AGENTS.md remains untouched.
- Review: three concrete P1 findings fixed with execution regressions: scheduler
  state injection/private traces; APFS case alias; receiver-side sibling
  exclusions/source identity. Independent reviewer delivered findings and
  completion notice; final worker tool status was an automated content flag.
  Lead verified each fix; no independent final approval or second broad review
  is claimed. See docs/isolation-001/review.md.
- Decisions: fail closed on unsupported execution; preserve explicit privileged
  owner full-access behavior for known native tools. No claim that argument
  filters isolate arbitrary code. Persistent profiles/data stay intact; delegated
  calls use stateless restricted views. Artifacts remain for parent/operator.
- Lessons Learned:
  - Mistake: relying on a short private-path denylist or case-sensitive path
    comparisons, and retaining only caller exclusions during delegation.
  - Root Cause: executable scheduler state and APFS aliases cross file boundaries;
    a receiver has a different set of sibling-private workspaces.
  - Future Trigger: changes to host-managed state paths, filesystem grants or
    execution identity during delegation.
  - Required Behavior Change: preserve absolute host-state exclusions across root
    grants, compare denial aliases conservatively, intersect both principals.
  - Verification Step: actual native Write/TaskStore, case/Unicode alias reads and
    real target-model requests prove private data/effects remain excluded.
  - Durable Memory Update: created project MEMORY.md with concise architecture
    facts and pointers; no global memory or production MEMORY.md changed.
- Known limits: no hard OS sandbox, hostile installed Python protection,
  arbitrary untrusted shell/browser/MCP, authenticated remote capability
  protocol, Windows broker or Linux enforcement run. Native rich-file parsing,
  private worker memory/skills and legacy scheduled tool calls are unsupported.
  Host model requests use cooperative cancellation; no process tree is launched
  by restricted workers. Nine ChannelsPage type errors remain a separate baseline
  defect; no frontend typecheck pass claimed. Detailed risks in the report.
- Next recommended steps: review restricted-mode compatibility before any merge
  or deployment. A separate scope must design and validate a supported OS
  execution service and authenticated remote authority before enabling them.
- Next-agent notes: final integrated receipts are at
  /private/var/folders/nn/3yz7zzyj617029dmpfzcvk940000gn/T/cowagent-isolation-regression-i8_f95v2.
  Baseline detached worktree and fictional probe artifacts are retained for
  review; paths and hashes are in docs/isolation-001. Preserve unrelated
  AGENTS.md and three conflicted PID files. No runtime restart performed.
- GitHub sync blocked: GitHub remote exists but current branch has no tracked
  upstream. This task requests a local dedicated-branch commit; no destination
  guessed or upstream set. The earlier audit branch push remains synchronized.

## 2026-11-06 23:22 EST — Codex — ORCHESTRATION-001 native audit

- Task: evaluate native delegation, concurrency, identity/workspaces, permissions,
  task persistence/recovery and supervisor verification before implementation.
  Baseline master c2c39a2e; dedicated branch audit/orchestration-001-native.
- Result: native peers have durable profiles/own workspaces; temporary workers
  share parent process/workspace/model. Two workers overlapped 0.086 s; two
  parallel batches at limit 2 produced four simultaneous workers (0.084 s).
  Correct artifacts passed independent checks; deliberately incorrect artifacts
  still received completed/done. These are synthetic path tests, not model-quality
  or provider-throughput measurements.
- Team: Codex lead owns probe integration, report, validation and Git; Luna/high
  lifecycle worker maps source and owns the persistent-peer probe; Luna/high
  isolation worker maps boundaries and owns permission/memory probes. One
  Terra 6.1/high reviewer checks evidence fidelity across threads, processes,
  permissions and persistence, beyond routine Luna file inspection. Requested
  models accepted; effective models not independently exposed. Used STE Writing
  Plans/evidence guidance. No HomeBoss or external agent runtime invoked.
- Recovery: synthetic 401 failed only one worker; synthetic 503 retried and
  recovered. Cancel/timeout returned while a model call was still blocked; rows
  remained running until worker exit, then cancelled. Process termination during
  a pending worker left raw running/history-interpreted interrupted. New-process
  explicit resubmission created a new run, not checkpoint continuation. No full
  web-server/service-manager restart was claimed.
- Authority/state: Explore Write lookup failed; inherited read-only and direct
  outside-workspace Write were denied. Fixed Python through native Bash wrote
  only a fictional sibling marker outside workspace/temp roots, demonstrating
  best-effort scope. Memory tool copies called the fictional parent manager.
  Peer handoffs retained 2 runs/2 user turns in the shared DB with separate
  worker scopes; worker-b could not load worker-a history. All artifacts remained
  in new disposable roots. Bash's ~/.cow/.env lookup was redirected to a missing
  fixture, and inherited provider environment variables were removed.
- Source findings: per-call rather than global worker cap; best-effort run
  recording; no durable worker dispatch/resume queue or mandatory verifier;
  no per-action approval handshake in inspected delegation/permission paths.
  Permission-check exceptions fail open; unknown tools need stronger capabilities.
  PeerTransport supports other CowAgent deployments; no native external CLI
  runtime adapter found. The asset guide's memory-tool blocklist is stale.
- Changes/files: only this ledger and docs/orchestration-001/{README.md,plan.md,
  probe.py,permissions_probe.py,delegation_probe.py,results.json,tests.json}.
  No product implementation, instruction, identity or production configuration
  changes. No self-evolution, production credentials, network services, PR or merge.
- Commands/tests: isolated synthetic config and blocked socket.connect;
  pytest.main over the 19 files in tests.json: 394 passed, no failures/skips in
  12.12 s. Final `.venv/bin/python docs/orchestration-001/probe.py --output
  docs/orchestration-001/results.json` passed all required observations with no
  permission skips. All three probes passed F-class Ruff and py_compile; source
  diff against c2c39a2e is empty outside docs/ledger. Receipt reconciliation and
  self-review completed; audit source label checks real HEAD and baseline diff.
- Review corrections: specify arithmetic requirements inside worker briefs;
  assert non-skipped permission results; record/verify actual source revision.
  Also align the observed denial marker with its write target, retain default
  Bash safety mode, and pin the peer fixture's global registry to the same
  synthetic registry as the bridge. Corrected probes rerun successfully.
- Decisions: compare BullGod to capabilities in this brief; no separate BullGod
  specification was found. Recommend capability/OS isolation, durable task/attempt
  and recovery contracts, mandatory verification, global admission, then a thin
  external-runtime adapter/approval contract. None implemented before review.
- Lessons Learned:
  - Mistake: testing an output predicate that the worker was never assigned,
    or treating a successful probe exit / durable run row as proof of supervision.
  - Root Cause: fixture requirements, assertion gates and source identity were
    incomplete; native run status records execution rather than correctness.
  - Future Trigger: orchestration audit using scripted models or mocked startup.
  - Required Behavior Change: put acceptance requirements in task briefs, identify
    substituted boundaries, assert every claimed observation and pin actual code.
  - Verification Step: wrong-artifact negative case, real tool/permission/SQLite
    paths, process death/new process, source match and independent evidence review.
  - Durable Memory Update: findings are in the audit README; MEMORY.md update:
    not needed (no project file, no architecture or instruction changes).
- Known limits: no live provider/remote peer/external CLI, full web restart,
  distributed stress or native Windows test. Temporary workers are not sandboxed;
  no claim of exactly-once recovery. Existing ChannelsPage baseline unchanged.
- Next recommended steps: review docs/orchestration-001/README.md, confirm the
  BullGod capability/isolation and recovery contract, then authorize a separate
  implementation scope. Do not implement audit recommendations automatically.
- Next-agent notes: final scratch workspace is
  /private/tmp/cowagent-orchestration-2sbcc0_h; regression JUnit/selection at
  /private/tmp/cowagent-orchestration-tests.YZXKyi. Preserve unrelated untracked
  AGENTS.md and three conflicted PID files. Dedicated branch is local only.
- GitHub sync blocked: GitHub remote exists but current branch has no tracked upstream.
  No upstream guessed, push requested, PR created or merge performed for this audit.

## 2026-11-06 22:45 EST — Codex — Integrated release and master merge

- Task: stop optimization, consolidate SQLite plus Phases 1–4, run one integrated
  regression/release review, merge verified work to the fork's master. Keep the
  nine pre-existing ChannelsPage type errors visible as a separate baseline.
- Result: release gates passed with that explicit baseline exception. Local
  master fast-forwarded 19e84350 -> 8eef97dc; reviewed/merged tree hashes match
  b479ffd25382bdada656cf906a86ab94d5a1c6b9. Consolidation edits are docs only.
  No code fix, new optimization, branch deletion, deployment or runtime restart.
- Team: Codex lead owns regression, SQLite snapshot/restarts, consolidation and
  Git; Luna/high verifies frontend/build and reproduces the exact baseline;
  one Sol 6.1/high independent reviewer checks cross-module data-integrity,
  context-budget and accounting invariants. That combined review exceeds routine
  Luna lookup work. Requested models accepted; effective models not independently
  exposed. Used STE branch-completion skill and efficient-evidence rule; existing
  merge authorization supersedes its options menu. No HomeBoss.
- Commands/results: private-COW_DATA_DIR `.venv/bin/python -m pytest -q -rA`
  across the 85 files in release-verification.json: 867 passed/15 skipped in
  16.20s. `COW_BROWSER_NATIVE_TEST=1` reran the seven opt-in browser skips:
  7 passed with private Chrome profiles. Unique result: 874 passed, 8 Windows-only
  skips (2 path-separator, 6 PowerShell). One collection used the known real-web
  API-before-stub order. No failures or errors.
- Frontend: `node --test tests/test_usage_display.mjs` 8 passed; changed JS syntax
  checks passed. Desktop `npm run build` passed. `npx tsc --noEmit -p tsconfig.json`
  FAILED, exit 2, with the same nine ChannelsPage TS2322 errors at both 19e84350
  and 8eef97dc using identical dependencies. Normalized logs byte-identical; file
  unchanged. This check is accepted baseline failure, never recorded as passing.
- Other checks: F-class Ruff passed on 34 changed Python files; all compiled;
  diff checks passed. Independent review found no actionable must-fix issue.
  Post-merge core smoke passed 61 storage/FTS/accounting/usage/title tests; these
  repeat existing cases and are not added to the unique count.
- Runtime evidence: new private workspace, two SQLite online backups from
  read-only/query-only sources. Three fresh processes called normal TestPilot
  memory setup, registered both memory tools, returned the same indexed result
  with one FTS MATCH each and LIKE blocked. WAL, both FTS indexes and integrity
  passed. Snapshot history row hashes preserved: 11 sessions/33 messages/14 runs.
  Config plus 33 active workspace file hashes unchanged. No production DB writes,
  deletion, replacement or rebuilding. Source remains outside Projects backup.
- Integration replay: existing benchmark on the fresh copy, no --live flag;
  all 16 tools, identical first/second system/tool blocks, successful FTS replay.
  No new provider requests; retained live phase evidence kept at its original
  scope. No new full UI/provider run, embeddings, native Windows or packaged
  desktop release. Existing build warnings and checkout/PID sync risk remain.
- Files: this ledger, efficiency README, new release-review.md and
  release-verification.json, new docs/known-issues/channels-page-typecheck.md.
- Decisions: merge the tested tree and retain the baseline as a separate defect;
  preserve measured limits (Phase 3 adds no proven cache gain; Phase 4 is a small
  synthetic title sample). Dynamic discovery and further optimization deferred.
- Lessons Learned:
  - Mistake: equating a successful production bundle with a clean renderer
    typecheck, or adding repeat-test counts as new coverage.
  - Root Cause: bundle/transpile and strict type checking are separate commands;
    native and post-merge checks repeat part of the integrated selection.
  - Future Trigger: release consolidation with known failures or repeated gates.
  - Required Behavior Change: reproduce baseline failures on the old revision
    with the same dependencies and report distinct checks and unique coverage.
  - Verification Step: identical baseline diagnostics; tree equality at merge;
    unique JUnit counts, post-merge core smoke, and preserved DB row hashes.
  - Durable Memory Update: release review and separate baseline issue document
    the evidence. MEMORY.md update: not needed; no project file exists and no
    instruction/identity/global memory file changed.
- Next recommended steps: none for this authorized consolidation. Address the
  documented ChannelsPage type mismatch as a separate task if requested. Do not
  resume token optimization or dynamic tool discovery without new direction.
- Next-agent notes: private backend/snapshot evidence at
  /private/tmp/cowagent-release-rmkpu4fm; frontend/base comparison at
  /private/tmp/cowagent-frontend-checks.gJt5tJ. Preserve untracked AGENTS.md and
  three conflicted PID files. The lead commits this docs-only consolidation on
  master, pushes existing origin/master, fetches and requires HEAD...@{u}=0 0.

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
