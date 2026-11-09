# AI handoff ledger

## 2026-11-08 22:58 EST — Codex — DISCOVERY-002 publication; live gate BLOCKED

- Result: Gate A PASSED (PR #3 merge 40958f39, master closeout f6593497 with passing
  automatic master CI). Gate B implementation, fixtures and review pass, but
  required integrated live acceptance is BLOCKED by actual APFS ownership
  enforcement and group-writable ancestry. No live eligibility is certified.
- Team: Sol 6.1/high bounded production and independent security review, justified
  by cross-component authority/provenance and Darwin ABI reasoning; Luna/high
  independent acceptance, metadata preservation and hosted reconciliation. Lead
  owns source integration, actual rejection replay, documentation and Git sync.
- Changes/files: trusted discovery readers, authenticated inspect, read-only
  operator journal and Darwin ownership guard; two test files; 002 report,
  sanitized receipts and runner; MEMORY.md and this handoff. Details below.
- Tests/results: 356 integrated tests passed; independent corrective review PASS.
  Final hosted run 42558258829 on 10dac8d3 passed all five jobs: macOS 6023/39,
  each Linux 6016/46; 6062 named cases plus 93 subtests per job. All 54 new cases
  pass, no removed cases, exact prior skip identities retained. JavaScript,
  strict TypeScript/build and Ruff pass. Logs/artifact/XML/source hashes retained.
- Actual evidence: repaired-source read-only attempt stopped at config read with
  filesystem_ownership_ignored, before registry/binding/selection. Process,
  config/profile/model and aggregate conversation metadata unchanged. Separate
  private authority read found all three credentials/enrollments/tasks expired;
  journal counts/intents unchanged. Constructor guards were not reached in the
  blocked live run; do not call this complete integrated no-dispatch acceptance.
- Preservation/publication: draft PR #4 stays unmerged. Verified tracked source
  at upstream 0/0; final closeout is documentation-only, with no repeated model or
  test interactions. git fsck passed with same 40 dangling objects/no other
  diagnostics. All seven original untracked files, five recovery artifacts, both
  recovery refs and clean detached worktree preserved. No service restart.
- Decisions: retain fail-closed boundary and withdrawn mode-only permission
  request. No host chmod, ownership enablement, mount change, approval refresh,
  credential modification, model invocation or production activation. Project
  MEMORY.md records durable reader and filesystem constraints; no global update.
- Lessons Learned:
  - Mistake: mode-only remediation was proposed before mount ownership was checked.
  - Root Cause: statvfs omits Darwin's ownership-ignore flag.
  - Future Trigger: trusted evidence on macOS storage.
  - Required Behavior Change: verify native ownership enforcement before proposing
    mode changes; withdraw insufficient proposals and keep unsafe input rejected.
  - Verification Step: independent actual path/FD checks and six regressions pass.
  - Durable Memory Update: the rule is recorded in project MEMORY.md.
- Known issues: B6 integrated live scenarios remain incomplete. No authoritative
  native isolated proof/global free capacity or safe Codex executable attestation
  is available; expired authority and historical submitted task IDs cannot be reused.
- Next steps: separately review storage ownership impact and obtain explicit
  authority for any host remediation. Then rerun read-only actual discovery;
  establish current complete proof/enrollment/exact task approval and runtime
  admission before any later executor request. DISCOVERY-002 merge needs separate
  authorization. Keep all original runtime/config/profile/memory data intact.
- Notes: all ten completion questions are answered in docs/bullgod-discovery-002/
  README.md. Source tested 10dac8d3; final documentation preserves its code hashes.
  The goal is not achieved while B6 is blocked. This is the first blocked
  closeout after all independent implementation/publication work; do not change
  storage or rerun unchanged blocked probes without new authority/state.

## 2026-11-08 22:47 EST — Codex — DISCOVERY-002 ownership enforcement correction

- Task/result: actual APFS workspace ignores ownership. A mode-only change cannot
  establish trusted provenance. The pending 0775-to-0755 permission question was
  withdrawn; no host permission, mount setting, config or live authority changed.
  Gate A remains PASSED; Gate B trusted live selection remains BLOCKED.
- Team: same Sol 6.1/high production worker and independent reviewer for the
  security-sensitive Darwin ABI/authority correction; Luna retained first hosted
  CI evidence. Lead owns integration, actual read-only replay, docs and Git.
- Changes/files: new agent/external/filesystem_trust.py uses Apple's explicit
  statfs64/fstatfs64 ABI and MNT_IGNORE_OWNERSHIP. Trusted reader, operator and
  recovery guards reject ignored/unknown ownership. Old writable operator setup
  rejects before creating state. Linux keeps existing checks. Six targeted cases
  added to test_discovery_runtime_readers; acceptance runner sanitizes the new
  stop code. Updated 002 reports/receipts and project MEMORY.md.
- Verification: worker 107 tests passed; independent corrective review PASS with
  separate actual path/FD mount observations and no remaining finding. Lead's
  integrated 356 tests passed in 46.02s; Ruff F passed. Actual read-only retry
  stopped before registry/binding/selection with filesystem_ownership_ignored;
  all process/config/profile/model/aggregate-conversation metadata unchanged.
- Hosted: prior head b82117e9 passed all five jobs in run42556509225 (macOS6017,
  Linux6010 each; 6056 named cases/93 subtests; 48 new cases, no removed cases,
  unchanged skip sets). Receipt retained explicitly for that source. This
  corrective source requires a new hosted run before final publication.
- Decisions: ownership enforcement is separate from permission mode; statvfs
  masks the required Darwin flag. No unsafe fallback or synthetic live proof.
  MEMORY.md updated; no global memory update.
- Lessons Learned:
  - Mistake: mode bits were initially treated as sufficient owner-trust evidence.
  - Root Cause: macOS can ignore ownership, and Python statvfs masks that flag.
  - Future Trigger: owner-based authorization on a macOS mount.
  - Required Behavior Change: query the authoritative native mount flag; reject
    ignored ownership or unavailable API before trusted reads or state creation.
  - Verification Step: 0755/0600 paths on simulated ignored mounts reject; real
    workspace rejects and private temporary storage accepts; Linux bypasses API.
  - Durable Memory Update: project filesystem trust constraint now records this.
- Known issues/next: finish fresh hosted CI and final sanitized closeout. Actual
  integrated selection needs a separately authorized storage/ownership remedy;
  a mode-only chmod is insufficient. Retained credentials/approvals remain expired.
- Notes: draft PR #4 remains unmerged. Preserve original PID28093, seven original
  untracked files, recovery references/artifacts and detached worktree. No paid
  model, live task replay or new enrollment/approval is authorized by this fix.

## 2026-11-08 22:27 EST — Codex — DISCOVERY-002 draft publication and live trust blockage

- Task/result: Gate A PASSED; PR #3 integrated as 40958f39 and automatic master
  CI passed. Gate B source is implemented/reviewed, but trusted live selection
  is BLOCKED at config ancestry (non-sticky group-writable volume, mode 0775).
  No guard bypass, filesystem permission change, new approval or runtime launch.
- Team: Sol 6.1/high production and independent review for cross-component
  provenance/authority/IPC reasoning; Luna/high independent fixtures, live
  metadata/preservation and hosted evidence. Lead owns integration/docs/Git.
- Changes/files: agent/discovery trusted readers and diagnostics; narrow
  agent/external read-only journal/inspect hooks; two new test files; 002 plan,
  report, runner, focused/review/preservation receipts; project MEMORY.md.
- Checks/results: 350 focused tests passed, including 48 new cases; Ruff F and
  runner syntax passed; independent review PASS after four corrective findings.
  git fsck --full passed, 40 unchanged dangling objects/no other diagnostics.
  Seven original untracked files, five recovery artifacts, both recovery refs
  and clean detached worktree preserved. Hosted 002 matrix pending publication.
- Live evidence: actual strict config read stopped before registry loading or
  selection. Separate service metadata/counts remain unchanged. Safe private
  authority inventory is separate evidence, not a replacement trusted registry.
  Missing native/Codex proof or admission remains unknown; no model call made.
- Decisions: retain guard; publish a draft with explicit blocker; no 002 merge.
  MEMORY.md updated with trusted-source, full-proof and frozen-enrollment rules.
- Lessons Learned:
  - Mistake: live source ancestry was checked only after implementation fixtures.
  - Root Cause: private temporary fixtures did not model the external volume's
    group-write permission.
  - Future Trigger: connecting trusted readers to existing files on shared storage.
  - Required Behavior Change: inspect owner/mode/canonical ancestry before assuming
    trusted config or proof readability; keep unsafe evidence rejected.
  - Verification Step: actual path rejection is preserved and reported; any
    future approved host permission change needs a fresh read-only acceptance.
  - Durable Memory Update: recorded in project MEMORY.md; no global memory change.
- Known issues/next: complete hosted matrix and sanitized evidence publication,
  then obtain maintainer direction for the storage trust boundary. Credentials
  and retained approvals remain expired. No positive live selection is claimed.
- Notes: source commit 7985be47 is based on verified master f6593497. Preserve
  original service PID 28093 and all unrelated files. Do not merge 002 or refresh
  live authority to convert this blocked result into a pass.

## 2026-11-08 22:04 EST — Codex — DISCOVERY-002 trusted readers; Gate B in progress

- Scope: active user goal is the DISCOVERY-002 attachment. Gate A is complete:
  PR #3 merged 40958f39, master CI 42550651190 passed, sanitized integration
  report published in docs-only master f6593497 at 0/0. Gate B branch
  codex/bullgod-discovery-002 starts at f659349785acf98905901a5cc53921436a109dbc.
  No 002 merge or production activation authorized.
- Team/ownership: Sol 6.1/high production worker discovery002_runtime_readers owns
  agent/discovery, narrow agent/external hooks and test_discovery_runtime_readers.
  Luna/high discovery_native_audit owns test_discovery_runtime_acceptance only.
  Luna/high discovery002_gate_a_preservation owns the read-only acceptance script
  under docs/bullgod-discovery-002 and private metadata receipts. Sol 6.1/high
  discovery002_gate_a_review owns the one independent Gate B review. Stronger
  production/review routing is justified by cross-component provenance, HMAC,
  SQLite and accidental-dispatch boundaries. Lead owns docs/integration/Git.
- Implementation: ReadOnlyNativeConfiguration, ExistingRuntimeBinding factory,
  TrustedDiscoveryHost; operator/audit/probe provenance and current fingerprints;
  read-only operator/approval opening; explicit authenticated inspect on existing
  adapters before request-row writes; select/revalidate never contact runtimes.
  Source callbacks remain backward compatible. No credentials/approvals minted.
- Verification: core broader 191 tests passed, then 66 affected after refinements;
  independent acceptance 19 passed. Parent integrated 330 passed before review fixes.
  Ruff/diff checks passed. No final hosted Gate B gate or PR yet.
- Review findings under correction: disabled native profile aborted all candidates;
  negative runtime observation lacked expiry; inspection did not compare the
  running adapter's frozen enrollment; historical focused probe receipt checked
  only 4 source files instead of binding the full tested source. Core owns fixes
  and regressions; acceptance owner updates positive fixtures to full-source-bound
  regression evidence. Same reviewer will check only corrective diff afterward.
- Actual records: all retained named and Codex enrollments/task approvals expired;
  named approved source differs from current source. Actual Codex runtime ID is
  acceptance-runtime. Socket files remain but prove no availability. Exact approved
  probe bytes found: agent-routing-003/merge-final-regression.json and
  external-002b/authority-probes.json. No live receipt was replaced or refreshed.
- No-dispatch baseline: original PID 28093 healthy; metadata-only aggregate counts
  sessions/messages/runs: default 4/7/6, testpilot 8/30/11, testpilot2 1/2/1. SQLite
  authorizer permits only agent_id COUNT/grouping on these tables; no content,
  title, transcript, memory-chunk or usage-extras reads. Actual acceptance is running
  under separate instrumentation and must be repeated only if final source changes.
- Decisions/limits: operator provenance is private-account trust, not signed audit
  or protection from same UID/root. Native isolated capability proof/global free
  capacity and safe Codex executable attestation remain unavailable where existing
  infrastructure cannot establish them. File config is not live in-memory/env
  attestation. Final Gate B likely PARTIAL; synthetic fixtures must not fill live
  proof gaps. Every result remains dispatch_permitted=false.
- Lessons Learned:
  - Mistake: partial source-file coverage in an authentic receipt could be treated
    as proof for a newly enrolled but incompletely tested source tree.
  - Root Cause: content/provenance matching was conflated with complete tested-source
    applicability across authority and model dependencies.
  - Future Trigger: importing historical capability evidence after source changes.
  - Required Behavior Change: require a complete receipt-bound source fingerprint;
    reject weaker schemas even if their content hash has operator approval.
  - Verification Step: old approved four-file receipt under changed dependency
    must remain unverified; full-source-bound disposable receipt can qualify.
  - Durable Memory Update: pending final validated contract; no global memory update.
- Next: finish four review fixes, final live read-only acceptance and no-dispatch
  comparison; close the same review; run affected integrated checks; publish
  implementation/report/draft PR and full hosted matrix; reconcile receipts and
  upstream 0/0. Preserve all seven untracked originals, recovery artifacts and
  original service; no model calls, profile/memory/provider/credential changes.
- Notes: task evidence root cow-discovery002-y05588lk under host temp; Gate A
  receipts in gate-a, actual inventory/validation in gate-b. Runtime count script
  and before baseline are in /private/tmp/cow-discovery-002-gatea-rFolPk. Production
  worker should change only concrete review findings; coordinate acceptance rerun.

## 2026-11-08 21:30 EST — Codex — DISCOVERY-002 Gate A integration passed

- Task/result: owner authorized DISCOVERY-001 integration. PR #3 marked ready
  and merged normally with expected-head 9293315e as 40958f39. HEAD/master/
  origin/master equal the merge at 0/0. Gate B remains unstarted until this
  report/receipt closeout is published.
- Team: Luna/high verified Git/runtime preservation and collected hosted CI;
  Sol 6.1/high independently reviewed the seven source/test files and existing
  identity/proof/approval/authority/execution dependencies. Stronger review was
  required for consequential cross-component security reasoning. Lead owned
  integration, focused validation, docs and Git. STE branch completion/review used.
- Changes/files: documentation only under docs/bullgod-discovery-001 (integration
  report, premerge/postflight/hosted receipts and README), MEMORY.md and this
  handoff. Existing implementation is unchanged from validated source ff09850d.
- Tests/results: 258 focused discovery/native/adapter/operator/recovery tests
  passed; one disposable SQL-authorizer probe passed. All seven operator/external
  tables retain identical rows, zero total_changes and zero mutating SQL attempts.
  Only BEGIN/SELECT/COMMIT traced. Independent review PASS, no open findings.
  Existing hosted evidence hashes match; automatic master Tests run 42550651190
  passed all five jobs. Reconciled logs/JUnit match all 6,008 named cases and
  exact prior skip sets: macOS 5,969/39; Linux 5,962/46; 93 subtests each.
- Integrity/preservation: pre/post git fsck --full passed with 40 preserved dangling
  objects and no other diagnostics; seven original untracked/five recovery
  artifacts/both recovery refs preserved; detached worktree clean. Original
  PID 28093 remains healthy at 127.0.0.1:9899 with config/provider/profile hashes,
  memory/database metadata unchanged. No private memory content read.
- Decisions: reuse source-equivalent PR evidence; normal merge only; update
  inactive local master through non-forced fast-forward fetch before switching
  to the identical tree. Closeout docs use [skip ci] and preserve tested code.
- Lessons Learned:
  - Mistake: a nominally read-only SQLite observation can be confused with
    filesystem immutability.
  - Root Cause: ordinary connection/WAL housekeeping is distinct from record DML.
  - Future Trigger: approving observational journal readers.
  - Required Behavior Change: inspect the call graph and verify zero DML plus
    unchanged records; state any connection bookkeeping limit explicitly.
  - Verification Step: SQL authorizer, total_changes and all-table snapshots.
  - Durable Memory Update: project MEMORY.md updated; no global memory update.
- Known limits: Gate A does not certify live proof/admission for any target.
  Missing host readers remain Gate B work. Ordinary Windows/native-browser
  exclusions stay recorded; no production activation or service restart.
- Next: once this source-bound closeout is synchronized, create
  codex/bullgod-discovery-002 from verified master and implement trusted runtime
  evidence/read-only admission under the supplied goal. Do not merge 002.
- Notes: private Gate A evidence root is cow-discovery002-y05588lk/gate-a under
  the host temporary directory. Preserve all original artifacts and service.
  Verify final master 0/0 after closeout push; then document exact 002 branch base.

## 2026-11-08 20:56 EST — Codex — BULLGOD-DISCOVERY-001 PASSED; draft PR #3

- Task/result: internal capability discovery, eligibility and deterministic
  selection are implemented, validated and independently reviewed. No dispatch
  path or activation was added. Baseline master 0805c82e; branch
  codex/bullgod-discovery-001; draft PR #3 remains unmerged.
- Team: Luna/high native and external source auditors; native worker then owned
  acceptance tests, external worker owned hosted receipts. Sol 6.1/high core
  worker and one Sol 6.1/high reviewer were selected because identity/proof/
  approval/authority integration required consequential cross-component reasoning
  beyond routine Luna work. Lead owned scope, integration, docs, checks and Git.
  Model requests were accepted; independent effective-model attestation is absent.
- Changes/files: new agent/discovery contracts, derived sources, service and API;
  additive read-only ApprovalJournal.preview_admission; two discovery test files;
  docs/bullgod-discovery-001 ADR, schema/integration report and receipts; project
  MEMORY.md and this handoff. Existing execution methods remain unchanged.
- Checks: clean tracked baseline and exact master/upstream; pCloud six Backup
  roots with no checkout/Git overlap and zero Sync rows. Original process 28093,
  health 200, config/provider/profile hashes and memory/DB stat metadata unchanged.
  Seven original untracked files, five conflict artifacts, both recovery refs
  and the clean detached worktree preserved. No private memory content read.
- Validation: isolated focused tests: 224 passed, including 52 new discovery cases;
  Ruff F, compilation, diff and receipt/link checks passed. Hosted Tests run
  42546970682 on source ff09850d: macOS 5,969 passed / 39 skipped, each Linux 5,962 / 46,
  93 passing subtests each; all 52 new cases pass; prior skip sets unchanged. JavaScript 39 + 5,
  strict TypeScript, desktop build and changed-file Ruff passed. Named test/skip
  reconciliation and raw log/JUnit hashes are in hosted-validation.json.
- Review: one independent engineering review PASS after correcting both P2s:
  explicit native source token before registry.get; actual execution budget
  compared with caller maximum/deadline/proof ceiling. Added explicit common
  disabled-identity reason; disabled profiles were already rejected by registry.
- Decisions: no duplicate roster, scheduler, memory engine, public endpoint or
  automatic probes. Typed trusted-host proof and admission readers are required;
  unknown/stale evidence stays ineligible. Native isolated and named persistent
  context remain distinct; external adapters stay analyze_records-only. Every
  selection has dispatch_permitted=false and requires executor revalidation.
- Lessons Learned:
  - Mistake: candidate runtime ID was initially included in the shared task hash;
    the original timeout check also treated a caller maximum as actual runtime.
  - Root Cause: selection constraints were conflated with target-specific
    approval identity and configured execution behavior.
  - Future Trigger: comparing targets or applying caller budget constraints.
  - Required Behavior Change: omit only runtime_id from normalized selection
    task hash; still verify each full approved spec. Compare actual configured
    budget with both caller and evidence limits; never rewrite approvals.
  - Verification Step: two-target temporary operator journals; exact spec/scope
    mutation tests; actual 30 / proof 600 / request 900 qualifies and proof 20 denies.
  - Durable Memory Update: project MEMORY.md updated; no global memory update.
- Known limits: synthetic validation certifies no live target capability. Host
  proof/admission integrations are absent by default; admission is an observation,
  not a reservation. Cancellation is cooperative; no hard exit/cost/exactly-once
  claim. Current native source fingerprints changed, so historical live enrollment
  cannot be promoted to current proof. Ordinary CI exclusions remain explicit.
- Publication: implementation ed641066 and acceptance ff09850d published in draft
  PR #3. Closeout is documentation/receipt-only with [skip ci]; seven reviewed
  code/test hashes and all non-document tracked content match the successful CI
  source. Feature upstream 0/0 is checked after push/fetch; master stays 0805c82e.
  Original seven untracked files remain deliberately preserved. No merge.
- Next recommended step: maintainer integration review of draft PR #3 using the
  completed report and source-bound gate; merge only with explicit authorization.
  Any later Luna dispatch or live evidence refresh needs its separate scope.
- Notes: all eight completion questions are answered in the report. No live model
  call, service restart, profile/provider/credential/memory change or production
  routing change. Private raw evidence remains in the task temp root recorded
  by the focused and hosted receipts. Do not replay historical acceptance tasks.

## 2026-11-08 20:32 EST — Codex — BULLGOD-DISCOVERY-001 implementation/review in progress

- Task: implement internal derived capability discovery, deterministic eligibility
  and selection; no dispatch or production activation. Baseline master 0805c82e;
  working branch codex/bullgod-discovery-001. No merge authorized.
- Team: two Luna/high workers audited native and external source contracts; the
  native auditor now owns independent acceptance tests. Sol 6.1/high core worker
  owns the discovery package and read-only approval preview because identity,
  proof, approval freshness and permissions require consequential cross-component
  reasoning. A separate Sol 6.1/high reviewer performs the one required authority
  review. Lead owns integration/docs/validation/Git. STE design/planning/review used.
- Changes: agent/discovery contracts/sources/service/API; additive read-only
  ApprovalJournal.preview_admission; focused contracts tests. Architecture and
  source-of-truth decision at docs/bullgod-discovery-001/architecture.md.
- Verification: clean tracked baseline, exact master/upstream 0805c82e at 0/0,
  existing linked worktree clean, original seven untracked/five recovery artifacts
  hash-preserved. Current pCloud UI has six nonoverlapping Backup rows and zero
  Sync rows; window restored closed. Original runtime metadata captured privately.
  Final focused checks: 224 pass, including 26 core +26 acceptance and existing
  adapter/native/operator checks; Ruff, compile and diff checks pass. One
  independent review PASS after both P2 fixes. Full hosted matrix pending.
- Decisions: derived view over AgentRegistry and enrolled ExternalSupervisor
  bindings; no second identity or approval database. Explicit trusted-host proof,
  signed observation and admission readers; missing evidence remains ineligible.
  Current adapters support analyze_records only, so arbitrary Codex coding is
  denied. Selection always dispatch_permitted=false, requires execution admission
  revalidation, and creates no tasks/approvals/intents. Timeout/deadline cannot
  promise a budget tighter than the actual policy/authority fence.
- Lessons Learned:
  - Mistake: full external task hash initially included the candidate runtime ID.
  - Root Cause: target-bound approval identity differs from target-independent
    requirements used to compare candidates.
  - Future Trigger: selecting between separately enrolled runtimes for one task.
  - Required Behavior Change: selection hash omits only runtime_id from the fully
    normalized spec; every candidate still checks exact full spec and approval.
  - Verification Step: two-target real temporary operator journals and task-change
    adversarial tests; signed envelopes and no-intent assertions.
  - Durable Memory Update: project MEMORY.md records the discovery contract; no
    global memory update.
- Review fixes: require explicit source ID; compare actual execution budget to
  caller/deadline/proof ceiling. Common disabled-identity check is explicit.
  Original runtime and all preservation checks pass. Host evidence/admission
  callbacks are trusted integration dependencies, absent by default; no live
  eligibility claim. Admission is bounded observation without slot reservation.
- Next: publish implementation/acceptance commits and draft PR, run full hosted
  matrix, publish source-bound receipts/final report and required final
  handoff and verify feature upstream 0/0. Do not merge or run live models.
- Notes: preserve original runtime PID 28093, agent profiles/memories/providers,
  credentials, recovery refs and untracked files. Raw evidence/cache root:
  /var/folders/nn/3yz7zzyj617029dmpfzcvk940000gn/T/cow-bullgod-discovery-001-flohoqs6.
  Core owns agent/discovery + test_discovery_contracts; Luna owns
  tests/test_bullgod_discovery.py and tests/discovery_fixture.py. No shared edits.

## 2026-11-08 19:36 EST — Codex — INFRA-RELIABILITY-001B integrated and verified

- Task/result: owner removal of Projects from pCloud is verified. The known
  active backup exposure and current Git integrity are RESOLVED under 001B.
  Independent integration review passed; PR #2 merged normally as
  323fefcd49bae71bbf3c191e23cf7aaca48ecb21. Historical corruption cause remains
  unknown. Automatic master CI and operational postflight passed. BullGod
  capability-discovery/task-selection development is ready; no activation occurred.
- Team: lead owns scope, pCloud UI, integration, docs and Git. Two Luna/high
  workers verified runtime metadata and current PR/CI evidence. One Sol 6.1/high
  reviewer assessed combined Git integrity, synchronization coverage, runtime
  privacy and source-bound CI; these risks need stronger cross-component
  reasoning than routine fixture checks. STE branch completion/review guidance
  applied. Requested model identities are not independently runtime-attested.
- Changes/files: documentation only. Added backup-removal-verification.md,
  backup-removal-review.md and scoped pCloud/Git/PR/runtime/postflight receipts
  under docs/infra-reliability-001. Updated the main report, recovery instructions,
  migration-plan notice and project MEMORY.md. Migration is superseded; all
  checkout, Git metadata, worktree and runtime paths remain in place.
- pCloud: Projects absent, six remaining Backup rows (one active), zero Sync
  rows; no canonical overlap with checkout/.git or all 21 runtime metadata paths.
  Normal window reopen returns identical scope; original PID 891 retained.
  Read-only DB query locked; no bypass. No kernel watch-absence claim.
- Git commands/results: no-prune/no-autoGC fetch, before/after snapshots,
  git fsck --full and two 45-second reference monitors pass. All 177 effective
  refs reconcile. fsck preserves 40 dangling entries with no other errors.
  Integration monitor saw only intended master/tracking updates and HEAD switch.
  Seven original untracked files, five conflict backups and both recovery refs
  preserved. Existing detached worktree clean at c2c39a2e; no recreation.
- Runtime: original PID 28093/loopback listener and health HTTP 200 preserved.
  COW_DATA_DIR, three agent workspaces, roster, config/profile hashes and all
  recorded database/core-file stat metadata match before/after. Config and both
  target profile hashes also match historical receipts. No private memory read,
  model call, reset, provider/profile change or server restart.
- Review/CI: no actionable independent-review finding. All eleven implementation
  hashes equal c03d35e6; prior run 42536883493 applies to the docs-only candidate.
  Mac 5,917/39, each Linux 5,910/46, 93 subtests each, JS 39+5, strict TypeScript,
  build and Ruff passed. Master push run 42540144872 also passed all five jobs at
  merge 323fefcd with identical counts and exact named-case/skip sets. Five logs
  and three ZIP/XML artifact hashes reconcile. Docs-only commits do not claim CI.
- Integration: published candidate 7be6edade3569d46f297dda23b514678ac69565d was
  marked ready and merged with an expected-head check, without bypass. Merge tree
  equals candidate tree. Local inactive master advanced through a non-forced
  fetch of the exact published merge commit, then switched to master; this kept
  working files at the reviewed version throughout. HEAD/master/origin/master
  matched 323fefcd at 0/0. Final docs-only publication retains all implementation
  hashes and uses [skip ci]; lead verifies push/fetch/master equality and 0/0
  immediately after this commit. No pruning or forced update is used.
- Lessons Learned:
  - Mistake: initial Accessibility reads used a stale process name and a variable
    that collided with the System Events dictionary.
  - Root Cause: process name is pCloud Drive; outLines was interpreted as outlines.
  - Future Trigger: application identity or Accessibility collection failures.
  - Required Behavior Change: resolve by PID, use distinct variable names and
    distinguish failed reads from zero configured rules.
  - Verification Step: successful canonical path inventory and identical reopen
    evidence, with independent scope review.
  - Durable Memory Update: project MEMORY.md updated; no global memory update.
- Known limits: historical writer/Actions missing-event cause unknown; current
  configuration is not a kernel watch inventory. Old DB inode continuity was
  unrecorded. Browser/full Windows, floating dependency/action versions, existing
  warnings and Python socket guard limitations remain documented.
- Next recommended steps: none for INFRA-RELIABILITY-001B. BullGod discovery
  and task-selection development can begin as the next milestone. Production
  activation and further native acceptance remain separate authorization.
- Notes: preserve feature branch and all recovery/untracked files. Postflight is
  at merge 323fefcd; final closeout changes docs only. Raw evidence root:
  /var/folders/nn/3yz7zzyj617029dmpfzcvk940000gn/T/cow-infra-001b-0lhnsyxq.
  Runtime helper: /private/tmp/cow-infra-b-runtime-YAT2TR/snapshot.py. PR #2:
  https://github.com/hottweelz/CowAgent/pull/2.

## 2026-11-08 19:02 EST — Codex — INFRA-RELIABILITY-001 published assessment

- Task/result: investigation, branch implementation, hosted validation and review
  complete. Git reference integrity is BLOCKED; Actions execution is CONTAINED.
  BullGod discovery/task-selection readiness is No. Draft PR #2 stays unmerged;
  master and origin/master remain fe00855a9f7b896115b2268492e11aa82d9bdc10.
- Team: lead owns integration, validation, docs and Git. Luna workers mapped
  sync/API/CI, rehearsed migration, built the read-only watcher and repaired
  hosted fixtures. Terra 6.1 handled CI integration, linked-worktree topology and
  timeout/recovery diagnosis. One Sol 6.1/high reviewer checked consequential
  Git integrity, rollback, CI authority and final evidence; this needed stronger
  cross-component reasoning than routine fixture work. Requested models were
  explicit; effective worker model identities are not independently exposed.
  STE planning, systematic debugging, evidence and review guidance applied.
- Changes/files: .github/workflows/test.yml adds macOS 3.13/Linux 3.11+3.13,
  JS, strict TypeScript/build and fail-closed changed-file Ruff. scripts/ adds
  isolated CI/lint runners, explicit prerequisites and a bounded read-only ref
  watcher; tests/ adds corresponding checks and repairs IPC readiness and Linux
  process-reaping fixtures. agent/subagent/runner.py supplies a missing timeout
  reason before state/UI closure without changing specific errors or authority.
  docs/infra-reliability-001 contains the report, source hashes, failed/successful
  receipts, review and recovery procedures. MEMORY.md records durable rules.
- Git evidence: pCloud Backup actively includes Projects/CowAgent/.git without
  an applicable exclusion. Historical writer remains untraced; sudo tracing is
  unavailable. A 45-second watch/fetch/worktree check saw no mutation, which does
  not establish isolation. fsck passed with 40 dangling entries and no other
  errors; nothing was pruned. Separate-git-dir reporting and experimental bare
  topology rollback did not pass live-migration safety gates. No migration ran.
- Commands/tests/results: manual Windows run 42534178341 passed 11/5 with logs.
  Two automatic PR runs exposed and localized fixture/timeout races. Final
  automatic run 42536883493 at source c03d35e6fd0ca1f35ad125b881db39816090951c
  passed all five jobs: macOS 5,917 passed/39 skipped; each Linux 5,910/46;
  each has 93 passing subtests and 5,956 named cases from 708 tracked test files.
  JS 39 web+5 desktop, strict TypeScript, desktop build and Ruff F passed.
  Focused CI/watcher/IPC/timeout/tokenizer checks also passed; report has counts.
- Independent review: no open actionable finding. All eleven changed executable,
  test, dependency and workflow hashes match the tested commit. Five log hashes,
  three GitHub ZIP/XML hashes, exact JUnit counts/skips and build/static results
  independently reconcile. Review reused retained evidence without test reruns.
- Decisions: preserve failed evidence, recovery refs/backups and all seven original
  untracked files. No reset, forced push, conflict deletion, live database repair,
  pCloud change, service restart, native model replay or TestPilot change. The
  closing commit is documentation only and uses [skip ci]; it does not claim a
  separate CI run. Earlier native approvals do not cover this changed source.
- Lessons Learned:
  - Mistake: mountpoint-only checks missed backup scope; socket existence,
    process exit and recovery completion were treated as settled states.
  - Root Cause: pCloud Backup includes ordinary APFS paths; listener startup,
    orphan reaping and independent recovery deadlines expose transient states.
  - Future Trigger: ref conflicts, IPC readiness, orphan cleanup or timeout UI.
  - Required Behavior Change: inspect active backup mappings and actual states;
    require a successful migration/rollback rehearsal before live authorization.
  - Verification Step: direct UI/API evidence, deterministic fixtures, hosted
    matrix, source-bound receipts and independent review.
  - Durable Memory Update: project MEMORY.md updated in the implementation;
    no additional closeout update needed. No global memory update.
- Known limits: active Git backup hazard remains; exact writer and historical
  missing Actions event cause are unknown. Polling is not PID attribution or
  prevention. Python socket instrumentation does not confine native/subprocess
  networking. Browser integration remains separate; Windows execution covers
  only Bash. Floating Python/action versions and existing warnings remain.
- Next recommended steps: design and rehearse a Git layout with metadata and
  controlling pointers outside backup conflicts; preserve portable paths and
  linked worktrees. Seek live authorization only after that plan passes. Keep
  BullGod work paused. Review PR #2 explicitly before any integration.
- Notes for next agent: branch codex/infra-reliability-001 tracks its same-name
  origin branch. Source c03d35e6 was pushed/fetched at 0/0; lead repeats the normal
  push/fetch/rev-list gate for this documentation closeout before final handoff.
  Report: docs/infra-reliability-001/README.md. PR:
  https://github.com/hottweelz/CowAgent/pull/2. Preserve server PID 28093,
  existing detached worktree, seven original untracked files and all conflict
  recovery artifacts. Live runtime, pCloud settings and master remain unchanged.

## 2026-11-08 16:49 EST — Codex — AGENT-ROUTING-001..003 merged after integrated gate

- Task/result: the required full regression and compatibility gate passed.
  The maintainer authorized master merge and baseline repairs. Final native
  acceptance passed on the one explicitly authorized final fresh pair. PR #1 merged
  as 9577d6b5da831efbad0a208a26032d90b2ef812d. Local master fast-forwarded
  to origin/master; the merge tree exactly matches reviewed head 5527fd1f.
- Team: Codex lead owns integration, acceptance, documentation and Git. Luna/high
  workers handled test execution, evidence and bounded fixture repairs. Terra
  6.1/high repaired guest authorization and the journal race because those fixes
  span native permission and concurrent state paths. One Sol 6.1/high reviewer
  checked consequential authentication, memory and recovery boundaries and the
  final native evidence. Explicit model requests were accepted; effective worker
  model identities are not independently exposed. STE finishing, review and
  dependency guidance used. One final Luna/high read-only worker confirmed the
  conflict-ref evidence during Git closeout; the responsible writer is unknown.
- Changes/files: agent/permission/policy.py permits only exact bound guest/native
  wrappers, retaining PathGuard, FileBroker and restricted privileged denial.
  agent/external/operator_control.py rechecks only otherwise-private zero-link
  SQLite sidecars. The legacy001 caller guard resolves denied roots. Executor
  fixtures now use valid authority and exact tools. Other fixtures correct shell
  quoting, image accounting, FIFO buffering, DB fault-injection ownership and
  child-exit synchronization. docs/agent-routing-001..003 contain adapter documentation,
  acceptance evidence and integrated report. Project MEMORY.md records durable
  authority, journal and test-environment rules. See the complete PR diff.
- Commands/tests/results: isolated directory-mode pytest includes all 706 tracked
  test files. Final application-source macOS run: 5,920 passed, 24 Windows-only
  skipped, 93 subtests passed, exit 0. Final published b2ebaf2 Linux snapshot:
  Python 3.11.18 and 3.13.18 each 5,896 passed, 48 skipped, 93 subtests passed,
  exit 0. Linux uses non-root Debian 13/aarch64, SQLite 3.46.1, private writable
  copies and offline owned sockets. All Linux skips are classified; browser and
  optional dependency gaps passed on macOS. Later test-only fixture checks pass
  16/16 and 12/12 on macOS. Node tests 39/39, strict desktop TypeScript and build
  pass. Current 31-file Ruff F/AST passes. Lead reconciled both Linux JUnit totals,
  log/artifact hashes and all 31 changed Python hashes against current source.
- Evidence: merge-final-regression.json is immutable SHA 47d8ac15...ecc07;
  merge-linux-regression.json is SHA 9c739bb9...ec37. Final executable fingerprint
  remains c45ddab4...f2ae across all gates. merge-review.md links full receipts,
  failed attempts, fixture diagnosis, source hashes and independent review.
- Native result: fresh tasks 3eb473eb-440e-44f2-bad7-fdfe7f4ff865/testpilot and
  af67b10d-694d-48a0-850d-f872c5625232/testpilot2 returned 17,400/20,000 cents.
  Distinct registered identity, profile, memory, session, run and PID bindings
  pass independent checks; native windows overlap 9.822 seconds. Each has exactly
  one submit/native/publication intent. Authentication negatives pass; tools and
  guarded caller private opens 0; pre/post snapshots match; owned processes exited.
  Native models/configuration unchanged. Both earlier failed pairs remain
  non-replayable with zero publication; neither counts as successful acceptance.
- Decisions: preserve approval/recovery/source binding, MCP and unsupported
  remote denial. No model substitution, private-memory read by Codex, persistent
  service activation or webserver restart. No more native runs needed/authorized.
  Hosted Actions never dispatched despite valid trigger opportunities; cause
  unknown. No required hosted branch check exists. Complete local Linux matrix
  satisfies compatibility review, with the hosted limitation retained explicitly.
- Lessons Learned:
  - Mistake: stale executor fixtures lacked authority; journal checks assumed
    stable sidecar links; several fixtures depended on scheduler/buffer timing.
  - Root Cause: fixture contracts lagged runtime contracts, while concurrent
    SQLite unlink and process/pipe timing expose transient observations.
  - Future Trigger: tests enter real permission paths, concurrent journal checks
    inspect sidecars, or tests assert state immediately after fork/readiness.
  - Required Behavior Change: use exact valid tools/authority, narrowly recheck
    safe sidecars, synchronize observed state and scope injection to owned files.
  - Verification Step: full macOS/Linux suites, denial/replacement fixtures,
    four-process journal reproduction and independent review; FIFO 100/100 probe.
  - Durable Memory Update: project MEMORY.md updated; no global memory update.
- Known limits: Windows-only cases not executed. Linux is local aarch64, not a
  hosted x86_64 replay. Existing build warnings and background cleanup/logging
  diagnostics remain recorded. Trusted-host metadata/instrumentation does not
  prove OS confinement, remote provider identity or a full private-file inventory.
- Next recommended steps: none for this merge milestone. Hosted CI dispatch
  diagnosis, Windows execution, local conflict-writer investigation and persistent
  activation remain separate work.
- Notes for next agent: preserve the failed/private fixtures, immutable bound
  receipts, untracked AGENTS.md, four conflicted PID files and two conflicted test
  copies. Existing server PID 28093 remains. Task containers were removed; Docker
  Desktop was restored to its initial stopped state. Feature branch tracks
  origin/codex/agent-routing-003 and is retained. Master tracks origin/master;
  fetch/rev-list verified 0/0 after merge. This documentation-only closeout is
  follow-up records leave every tested Python hash unchanged.
  The seven listed untracked files are preserved. Local master and tracking refs
  later reverted to the old base without reflog entries; a closeout push was
  safely rejected. The rejected commit is preserved on
  codex/routing-closeout-ref-recovery. Its tree differs from the verified merge
  only in these two documentation files. The corrected closeout uses the verified
  remote merge as its explicit parent; no forced push. Generated invalid ref copies
  were moved byte-for-byte to the task-owned backup documented in merge-review.md.
  Packing the two verified master refs restored stable resolution; fetch and
  rev-list then passed at 0/0. This repairs local Git metadata, not the unknown
  conflict writer. Preserve recovery refs and backup evidence for later diagnosis.

## 2026-11-08 14:13 EST — Codex — AGENT-ROUTING-003 persistent named-agent pair

- Task/result: completed both named-agent adapter paths and independent live
  validation. PASSED: testpilot and testpilot2 retained separate registered
  identities, native context/memory, configured model routing and fresh sessions.
  Native run windows overlapped by 13.912 seconds. Branch codex/agent-routing-003
  starts at 2289860b; no master merge or persistent activation.
- Team: Codex lead owns design, integration, paired client/live run, validation,
  docs and Git. Luna/high diagnosed/fixed the scheduling fixtures and another
  Luna/high mapped the adapter. Terra 6.1/high implemented the adapter: identity,
  approval, native mutable state and memory ownership span several components.
  One Sol 6.1/high reviewer checked consequential cross-target authority/privacy
  boundaries and independently checked sanitized live evidence. Requested model
  selections accepted; effective delegated model identities are not exposed.
  Applied registry-listed STE debugging, planning and bounded review guidance.
- Changes/files: cowagent_native.py selects either enabled target, checks memory
  ownership and emits validated execution metadata; cowagent_adapter.py binds
  credentials to target and serializes each native instance; cowagent_cli.py
  adds target inspection/metadata; operator_review.py binds named runtime IDs.
  Three CowAgent test files cover selection, scope, aliasing, serialization,
  cross-target denial and recovery. Corrected tests/test_parallel_tool_calls.py.
  Added docs/agent-routing-003 plan, paired runner, fixtures, receipts, report and
  review. Updated project MEMORY.md and this ledger. Generic delegation unchanged.
- Fixture gate before implementation: reproduced four failures/two passes.
  agent=None caused authority evaluation failure, and toy tool classes lacked
  exact permission descriptors. Fixtures now use a real read-only context and
  registered SubagentTool; only execution is stubbed. Four affected cases, whole
  file 6/6 and broader five-file selection 60/60 passed before adapter changes.
- Commands/results: private COW_DATA_DIR focused native/adapter/enrollment/
  operator-review/approved-dispatch selection: 97 passed. Final 15-file focused
  regression: 202 passed in 5.02s. After review alias fix, native file: 22 passed,
  including three new symlink/hardlink cases. Final fixture-only Path.home
  isolation correction: five recovery cases passed; separate receipt preserves
  the original enrolled probe digest. Ruff F, AST/JSON/link checks and
  staged diff checks pass. Original and final source hashes retained separately.
  No full-suite claim or replay of accepted model work.
- Live invocation: docs/agent-routing-003/run_acceptance.py --execute used the
  existing config/registry with two private authenticated Unix-socket processes,
  not another webserver. Task c2613519-d79d-4d8b-bb68-db7041931507 (testpilot,
  PID 33418) net 17,400 cents; task 64299e66-5053-4560-898a-b9e5150e89b6
  (testpilot2, PID 33422) net 20,000 cents. Both accepted three rows/excluded two;
  distinct profile/memory/session/run/PID bindings independently checked.
  Both inherit custom/nvidia/nemotron-3.5-super-vl:free; no model was changed.
- Evidence: one submit/native/publication intent per task; exact artifact and
  dataset hashes checked independently. Signed target overrides and cross-target
  task specs rejected. Wrong credentials got no authenticated response, with
  endpoint liveness separately confirmed. Unapproved tasks denied; duplicates
  retained completed sessions. Native tool events zero, guarded caller private
  opens zero. Private fixture /private/tmp/cowagent-routing003-ll5hc8if retained;
  launch secrets/raw native logs are not published.
- Preservation: both native pre/post snapshots match profile/config/source and
  known context metadata. Owned processes exited; original listener PID 28093
  stayed on 127.0.0.1:9899. Native bookkeeping/index writes are permitted and not
  claimed absent; task/session receipts live in adapter/operator journals rather
  than manual chat history. No live DB reset, WAL/SHM rename, profile or config edit.
- Review/decisions: no remaining actionable finding. Corrected pre-initialization
  DB symlink/hardlink alias denial and made preservation failure block acceptance.
  One target per process isolates mutable native state; per-runtime work is
  serialized. Keep the two mechanisms distinct: restricted generic delegation
  versus approved persistent named context. Scope stays two targets and fixed
  fictional analysis. Settled native recovery history is allowed; startup work
  that could resume/verify remains blocked.
- Lessons Learned:
  - Mistake: stale fixtures bypassed valid Agent construction; initial path
    equality could accept an aliased DB, and acceptance completed before postflight.
  - Root Cause: tests omitted the real authority contract; path resolution erased
    ownership information; preservation was recorded without gating success.
  - Future Trigger: tests enter the permission gateway or new registered targets
    share a native runtime/storage environment.
  - Required Behavior Change: use registered tools/valid authority; check DB
    containment and inodes before opening; require preservation before completion.
  - Verification Step: original four failures reproduced, then 60 passes; alias fixtures prove
    Bridge uncalled; live exact results/bindings/intents/postflight independently
    checked. No accepted task rerun.
  - Durable Memory Update: project MEMORY.md records named selection, ownership,
    concurrency and fixture rules. No global memory update.
- Known limits: trusted-host evidence, not OS confinement or remote provider
  attestation. Metadata is not a private-file content inventory. External
  filesystem changes after preflight are not locked; same-runtime serialization
  does not serialize other manual sessions/processes. Cancellation cooperative;
  no live crash/revocation campaign or hard cost/all-descendant guarantee.
- Next recommended steps: none for AGENT-ROUTING-003. Broader target enrollment,
  memory-aware output contracts or persistent service activation need separate scope.
- Notes for next agent: preserve the private receipt fixture and existing server.
  Preserve untracked AGENTS.md/four conflicted PID files. Two additional test
  conflict copies appeared while replacing the fixture; cause unproven, retained
  unstaged. Tracked path was recovered and patched in place. Publish this branch
  to origin with same-name upstream, fetch and verify 0/0; do not infer master merge.

## 2026-11-08 13:48 EST — Codex — AGENT-ROUTING-002 live native delegation audit

- Task/result: completed the audit and live test on the existing service.
  Assessment PARTIAL: default invoked native agent_delegate for testpilot and
  testpilot2; both calculated correctly and completed once, sequentially. Both
  returned agent_id CowAgent. Native target routing is verified, but persistent
  receiver instructions, skills, memory manager and history are excluded.
- Team: Codex lead owns live invocation, collection, integration, handoff and
  Git. Luna/high workers mapped the console path and authority/recovery path;
  the latter ran focused tests. One independent Luna/high reviewer checked the
  arithmetic, source, sanitized evidence and report. Requested models accepted;
  effective worker model identities are not independently exposed.
- Changes/files: docs/agent-routing-002 contains fixed fictional tasks, a
  one-submit console probe, scoped read-only collector/offline reconciliation,
  runtime/events/results/postflight/test/static receipts, report and review.
  Updated project MEMORY.md and this ledger. No application code changed.
- Runtime: reused PID 28093 on 127.0.0.1:9899 with the existing TestData config
  and CowAgent-Runtime workspace. No second server/restart/config/profile/model
  or permission change. One fresh default session added only the two roster
  members. Self-evolution and external API remained disabled.
- Live results: parent session audit-routing-002-688ad1f790384d589c86c02672885352;
  tasks 5d027a42-3314-4424-8ea4-be99c00f5e22 and
  998f52a9-f68d-49ea-a182-2c880f04c4bf. A net 17,400 cents; B net 20,000 cents;
  counts and exclusions match. A ended 18:35:36.584Z, B began .616Z. Both frozen
  specs use custom/nvidia/nemotron-3.5-super-vl:free with no fallback. Two allowed
  supervisor tool decisions; no worker tool events in retained SSE or recovery
  effects. Independent verification does not trust the returned self-name.
- Writes/preservation: one new source session/roster preference, four message
  rows, three display run rows, two recovery tasks/attempts/verification rows;
  no receiver chat rows. Native verification remains unverified without caller
  check contracts; the audit independently checks arithmetic. Database bytes
  are not claimed unchanged. Config/registry/nine source hashes unchanged and
  known core-file metadata unchanged. Private memory bodies and prior chat
  contents were not read. Preserved AGENTS.md and four conflicted PID files.
- Commands/results: isolated COW_DATA_DIR pytest selection in focused-checks.json
  passed 55/55. Earlier expanded five-file selection: 56 pass, four parallel-safe
  fixture failures (agent=None makes permission evaluation fail before tool
  execution). Retained exact IDs/error; no product fix or full regression.
  Ruff F, AST/JSON parsing, offline reconciliation and staged diff checks pass.
  No accepted model interaction was rerun.
- Review/decisions: recommend both mechanisms with distinct contracts: native
  delegation for restricted ephemeral work; 001 authenticated adapter for
  persistent named context. The latter is still enrolled only for testpilot.
  Reviewer findings corrected exact target/attempt/event reconciliation and
  independently recomputed identity/result flags. SSE-to-journal correlation
  uses isolated session, unique target/task identifier and time; retained SSE
  has no shared durable task key. Raw summary hashes cannot be recomputed from
  sanitized output alone. No architectural change was made.
- Lessons Learned:
  - Mistake: the first collector assumed each receiver index held chat tables.
  - Root Cause: workspace memory ownership was confused with global namespaced
    conversation storage and source-owned display runs.
  - Future Trigger: checking delegated session persistence across agents.
  - Required Behavior Change: trace the conversation-store binding before a
    metadata query; use owner/session predicates and native target task fields.
  - Verification Step: scoped rows, exact two-target reconciliation and read-only
    independent review; the failed query caused no write or model replay.
  - Durable Memory Update: project MEMORY.md records live semantics, routing
    evidence and conversation-store ownership. No global memory update.
- Known issues/limits: wrong worker self-identity; generic context is intentional
  native behavior; four out-of-scope fixture failures retained. Local model
  configuration is not remote attestation. No hostile-host/OS isolation proof,
  live file-denial probe, cancellation/crash campaign or broad regression. Core
  metadata checks are not a full private-file content inventory.
- Next recommended steps: none for this audit. If persistent TestPilot2 access
  is needed, scope its adapter enrollment/validation separately; do not change
  native isolation or activate a service from this report alone.
- Notes for next agent: read docs/agent-routing-002/README.md. Keep the existing
  server running and preserve audit records and unrelated files. Branch is
  codex/agent-routing-002 from 90c3cd8f; publish to same name on origin, fetch and
  verify upstream 0/0. No master merge or deployment is authorized by this task.

## 2026-11-08 11:52 EST — Codex — AGENT-ROUTING-001 registered TestPilot experiment

- Task/result: proved one authenticated Codex delegation to the existing
  registered testpilot with its native prompt, inherited model, memory manager
  and execution path. Fictional read-only analysis passed independent arithmetic
  and artifact checks. Milestone complete; no master merge or production service
  activation. Branch codex/agent-routing-001 from master 9cd8c535.
- Team: Codex lead owns native entry point, enrollment, real acceptance, docs and
  Git. Luna/high mapped manual routing/contracts, wrote enrollment/native tests
  and independently verified retained evidence. Terra 6.1/high implemented the
  adapter: concurrent approval, cancellation and recovery exceeded routine Luna
  work. One Sol 6.1/high reviewer covered private-memory and atomic authority
  boundaries. Requested models accepted; effective worker identities not exposed.
  Applied registry-listed STE planning and delegation guidance.
- Changes/files: new agent/external/cowagent_adapter.py, cowagent_native.py and
  cowagent_cli.py; strict CowAgent enrollment variant in operator_review.py;
  three focused test files; docs/agent-routing-001 plan, runner, report, receipts,
  trace and review; project MEMORY.md and this ledger.
- Native path: registry-owned testpilot/TestPilot inherits custom provider and
  nvidia/nemotron-3.5-super-vl:free. Manual Nov 6 runtime routing logs and current
  source were traced. Existing agent_delegate intentionally omits persistent
  context, so the adapter uses native get_agent/run_stream under receiver identity
  and read-only permission with a fresh server-owned session. Caller attribution
  stays user content; no replacement system prompt/model or generic authority.
- Reused contracts: authenticated private Unix IPC, OperatorControl,
  ApprovalJournal, ExternalSupervisor and AnalysisVerifier. One-shot native and
  publication intents require current approval. Uncertain work never replays.
  Exact expected report equality gates publication; private raw output cannot
  escape in schema-valid text fields. No native chat/runtime source was changed.
- Commands/results: private-COW_DATA_DIR pytest on the 12 files recorded in
  focused-validation.json: 163 passed in 3.87s, no skips/failures. Ruff F,
  syntax checks and staged diff checks pass. Product source hashes match; one
  test trailing blank was removed with identical AST (final-validation.json).
  One real --execute acceptance finished in the existing TestPilot model with
  zero tool events; unapproved submission denied. Task 4bb04826-e64e-43d4-9c4c-a010777786eb
  has one submit/native/publication intent and stable session f96a59e3-108e-4b06-9ac8-55cebf1aac79.
  Seven records yield four accepted, three exceptions and net 18,000 cents.
  Independent Luna arithmetic, source hash, artifact SHA and SQLite metadata
  checks passed. No accepted model interaction was rerun for bookkeeping.
- Postflight: native config/profile/credential-file/source snapshot unchanged;
  zero context create/remove events; caller audit recorded zero private opens.
  Native start/completion metadata binds testpilot/model/session/run. The owned
  process exited. Private fixture /private/tmp/cowagent-routing-kwzz7xni retained;
  launch secret and raw native logs are not published.
- Review/decisions: no remaining blocker. Corrected config-level MCP and scheduler
  backup preflight, same-model provider fallback attribution, output parse-error
  privacy and provider agent/session metadata. Startup refuses unrelated work;
  native memory/index maintenance remains native-owned. Manual UI chat persistence
  is distinct from this adapter's task journal and fresh in-memory native session.
- Lessons Learned:
  - Mistake: initial preflight omitted fallback startup sources; initial output
    handling left a raw JSON exception and did not check same-model provider fallback.
  - Root Cause: primary config paths and final model name do not cover all native
    initialization/model routes; parser exceptions can retain private output.
  - Future Trigger: externally controlled access to a registered persistent Agent.
  - Required Behavior Change: trace primary and fallback routes; preserve routing
    metadata; normalize private-output errors and gate exact safe output.
  - Verification Step: negative MCP/backup/fallback/parser tests; actual registered
    execution metadata and independent artifact/journal/source checks.
  - Durable Memory Update: project MEMORY.md records named/native versus restricted
    child semantics, approval/export contract and trusted-host limits.
- Known limits: Python-open guard is not OS confinement or hostile same-account
  isolation. Provider is locally configured and checked, not remotely attested.
  Read-only task permission does not promise no native bookkeeping/index writes.
  Cancellation is cooperative; no hard cost/all-descendant guarantee. Restart and
  revocation have focused fixture coverage, not a new live crash campaign. No new
  full regression/UI replay; unchanged native paths retain prior baseline evidence.
- Next recommended steps: none for AGENT-ROUTING-001. Broader outputs, more targets
  or persistent activation require a separately scoped task.
- Notes for next agent: docs/agent-routing-001/README.md describes the trace,
  source/evidence limits and opt-in runner. Preserve unrelated untracked AGENTS.md
  and three conflicted PID files. Parent publishes this task branch to the same
  name on origin under the standing maintainer preference, then fetches and checks
  0/0. Do not infer a master merge or production activation from this experiment.

## 2026-11-07 23:37 EST — Codex — EXTERNAL-003B merge review and SQLite diagnostic

- Task/result: completed the maintainer-authorized merge review for EXTERNAL-003B
  and its EXTERNAL-003 dependencies from master edb70433 through b92c535f.
  Approved for master consolidation with the test-only correction below.
  Production orchestration and consequential external actions remain disabled.
- Team: Codex lead owns diagnosis, correction, docs, integration and Git sync.
  Luna/high traced test lifecycle and independently checked retained evidence
  and the fresh full regression. The existing Sol 6.1/high reviewer checked
  merge boundaries and the correction; concurrent authority and cancellation
  require stronger reasoning than routine Luna review. Requested models were
  accepted; effective delegated identities are not independently exposed.
  Applied STE systematic-debugging and finishing-a-development-branch guidance.
- Changes/files: tests/test_shared_db_recovery.py now waits for maintenance in
  all three fixture teardowns before deletion/log restoration; timeout fails and
  preserves the fixture. Added three event-barrier regression cases. Updated
  docs/external-003b README/review; added sqlite-diagnostic.md and
  merge-validation.json. Updated project MEMORY.md and this handoff.
- Diagnosis: maintenance opens a second SQLite connection asynchronously;
  foreground close does not join it. Deleting the fixture after that open but
  before its WAL pragma reproduces real SQLITE_IOERR_FSTAT (1802) on SQLite
  3.45.3. All three new cases failed before the correction with the exact native
  code/name, then passed afterward. The original log lacks a test-ID binding;
  exact historical case attribution remains unknown. This is separate from the
  previous renamed-WAL SHORT_READ (522), not proof of a new production failure.
- Verification: focused shared-db/storage-I/O/FTS selection: 40 passed in 3.62s;
  reviewer independently confirmed three barrier cases in 0.20s. Ruff F,
  in-memory compile and diff checks passed. Existing protected runner:
  `.venv/bin/python docs/external-003b/run_regression.py` — 1,530 pass, 15 skip,
  1,545 IDs/131 files, zero failures/errors. Fresh run.log has zero FSTAT/1802 or
  background-maintenance diagnostics; ten deliberate injected error records
  remain distinguishable. Seven exact native-browser receipts reuse unchanged
  hashes: 1,537 unique passes and eight Windows-only skips.
- Evidence/review: all 14 final native source hashes, eight regression static
  hashes and nine browser/UI hashes matched. Reused actual Codex success,
  revocation, host/native-intent crash and independent-verification evidence;
  no new model call. Reused Node39, strict renderer zero diagnostics and desktop
  build receipts with recorded warnings. No new blocking review finding.
- Decisions: fix the test resource lifetime rather than change production
  storage. Preserve original diagnostic/native/regression receipts and explain
  the correction in an additive merge receipt. Source under agent/ is unchanged
  from b92c535f. Native model, authentication, policy and production state remain
  unchanged. Consolidate into master and push both feature and master refs;
  verify equal integration trees and upstream 0/0 at closeout.
- Lessons Learned:
  - Mistake: fixture deletion assumed foreground close stopped maintenance.
  - Root Cause: asynchronous SQLite resource lifetime exceeded fixture lifetime.
  - Future Trigger: cleanup removes a database used by background work.
  - Required Behavior Change: join that work before deletion; timeout preserves
    the fixture and fails the check instead of deleting an active database.
  - Verification Step: barrier regression establishes the real open/delete order
    and full-suite log inspection distinguishes unexpected from injected errors.
  - Durable Memory Update: recorded asynchronous close and teardown ordering in
    project MEMORY.md. No global memory update.
- Known issues/limits: historical emitting test is unknown; native empty-thread
  history remains unavailable, not empty. Task-effect cancellation is not
  descendant-exit or hard-cost proof. Uncertain work never replays. Windows-only
  cases remain skipped and retained build warnings remain documented.
- Next recommended steps: explicit uncertainty resolution and operational
  credential/retention controls before any separately authorized activation.
- Notes for next agent: see merge-validation.json for exact receipts and hashes.
  Preserve untracked AGENTS.md and the three conflicted PID files. Do not infer
  production activation or new external authority from master consolidation.

## 2026-11-07 23:16 EST — Codex — EXTERNAL-003B approval-enforced dispatch

- Task/result: implemented and validated approval-enforced bounded analysis on
  feat/external-003b-approved-dispatch from 036d957f. Ready for review; no master
  merge or production activation. Consequential external operations remain out
  of scope and unsupported by the Codex adapter.
- Team: Codex lead owns lifecycle, adapter hooks, real acceptance, integration,
  docs and Git. Luna/high mapped runtime seams, migrated adapter fixtures and ran
  release gates. Terra 6.1/high built the shared journal/supervisor integration
  and adapted the native runner; interacting transactions and recovery exceeded
  routine implementation. One Sol 6.1/high architect/reviewer covered atomicity
  and uncertain cross-process effects. Requested models accepted; effective
  delegated identities not independently exposed. STE planning/review guidance.
- Changes/files: approved_dispatch.py; operator_control.py, supervisor.py and
  codex_adapter.py; test_approved_dispatch.py and updated test_codex_adapter.py;
  docs/external-003b plan, runners, README, review and native/regression receipts;
  project MEMORY.md and this ledger. Policy/model/authentication and live
  CowAgent state remain unchanged; no application worker or service registration.
- Contract: current approval and durable host/native/publication intent share one
  SQLite transaction in operator.db. Native intent follows fresh attestation.
  Prior intents never permit replay. Revocation/replacement writes cancellation
  fences with the operator decision. Polling and supervisor delivery share one
  cancellation claim; uncertain interruption requires explicit retry. Legacy
  analysis and caller-label approvals reject. Adapter reports cow.codex/2.
- Actual native evidence: installed CLI 0.165.0 and existing selected runtime.
  Unapproved/revoked/legacy/unsupported requests denied. One approved native turn
  survived supervisor SIGKILL after acceptance; same identity, no duplicate and
  independently verified seven-record artifact (net 13,000 cents). Revocation
  after actual attestation prevented native admission. A second model turn was
  revoked during observed activity; scoped cancellation confirmed, no artifact.
  Adapter SIGKILL after native intent but before outbound turn/start preserved
  identity/intent and did not replay or publish; running/unknown stays explicit.
- Commands/results: real --execute acceptance initially passed denials/success
  then encountered empty-thread history RPC -32600. Corrected receipt collection
  and --resume continued only uncovered cases with new task IDs; final passed.
  Config hash remained 7d926393...874cc throughout; captured owned groups cleaned
  up, no all-descendant/cost guarantee. `.venv/bin/python
  docs/external-003b/run_regression.py`: 1,527 pass, 15 skip, 1,542 IDs/131 files,
  zero failures/errors. Seven exact unchanged browser cases reused: 1,534 unique
  passes/eight Windows skips. Fresh Node39, strict renderer zero diagnostics and
  desktop build pass; recorded existing warnings. Ruff F/compile passed for eight
  changed/new files. Native/product and static hashes match current source.
- Review: one blocking cancellation claim overlap corrected and independently
  confirmed by private IPC lost-interrupt/reconcile/explicit-retry regression.
  No remaining blocking source finding for this scope. Unknown-task rejection
  normalized; shared-journal foreign keys enabled; legacy bypass tested.
- Lessons Learned:
  - Mistake: two cancellation paths could independently deliver the same intent;
    the first harness also assumed fresh observers could list empty threads.
  - Root Cause: durable cancellation delivery needs shared ownership; public
    history availability is separate from whether a turn/start was attempted.
  - Future Trigger: multiple cancellation/recovery paths or pre-turn crash probes.
  - Required Behavior Change: claim delivery before IPC and preserve uncertainty;
    record missing history explicitly and capture outbound RPC attempt metadata.
  - Verification Step: explicit-retry regression and actual continued acceptance;
    accepted success was reused after product/config hashes matched, never rerun.
  - Durable Memory Update: recorded atomic gates, claim ownership, intent ordering
    and empty-thread history limits in project MEMORY.md.
- Known issues: no human-presence or hostile same-account isolation claim.
  Revocation after intent cannot retract authorized turn/publication. Adapter
  restart lacks a live client for interruption. A separate non-failing temporary
  test index logged SQLITE_IOERR_FSTAT (1802); root cause unconfirmed and recorded,
  not suppressed or represented as a clean log. No memory-code change in scope.
- Next recommended steps: owner review before merge/activation; then explicit
  uncertainty resolution and operational credential/retention controls. Investigate
  the separate temporary-index diagnostic without modifying production memory.
- Notes for next agent: real fixtures retained at
  /private/tmp/cowagent-003b-qy6xduds; IPC secret stays private and is not published.
  Receipts preserve the initial observer failure. Push this completed branch and
  verify upstream 0/0 at closeout. Preserve untracked AGENTS.md and three conflicted
  PID files. Master remains edb70433; do not infer activation authority from tests.

## 2026-11-07 20:57 EST — Codex — EXTERNAL-003 local enrollment and approvals

- Task/result: implemented the owner's selected enrollment/approval focus on
  feat/external-003-operator-controls from fcfd0377. Local decisions are tested;
  live orchestration and real external actions remain disabled. No master merge.
- Team: Codex lead owns contract, state implementation, integration, docs and Git.
  Luna/high mapped existing authentication, built the CLI and implemented focused
  tests in bounded assignments. One Sol 6.1/high review covered OS identity,
  SQLite revisions, expiry and replay across boundaries; this needed stronger
  security reasoning than routine Luna work. Requested models accepted; effective
  worker identity not independently exposed. Used STE planning guidance.
- Changes/files: new operator_control.py, operator_cli.py and their two test
  files; EXTERNAL-003 plan, README, operator-review.md and operator-validation.json;
  project MEMORY.md and this ledger. Existing adapter, supervisor, native runtime,
  UI, production state and native credentials/configuration unchanged.
- Contract: derive operator identity from the local POSIX account, not a supplied
  label. Require private canonical state and trusted ancestors. One WAL/FULL
  transaction commits revisioned approval/revocation with an audit snapshot.
  Freeze scope/spec/review/enrollment revision and expiry. Duplicate requests
  expose historical receipts plus current state and cannot reinstate revocations.
  Re-enrollment invalidates older task approvals. All responses disable execution.
- Commands/results: pytest operator-control file 26 passed, CLI file ten passed,
  review/contract/supervisor regression 43 passed: 79 unique passes, no skips or
  failures in final runs. CLI acceptance used separate actual Python processes
  and disposable SQLite. Ruff F and in-memory compilation passed for four files.
  Retained unchanged release baseline: Python 1,456/eight Windows skips, Node39,
  strict renderer and desktop build pass with recorded warnings. No fresh native
  model/service calls; no redundant full UI/runtime replay.
- Review/corrections: no remaining blocking finding. Expiry now samples time
  after writer-lock acquisition; independent actual-clock contention rejected
  expired work with empty audit. Oversized numeric expiry becomes ProtocolError.
  Trusted ancestors are enforced. Missing-state error normalized. Corrected
  negative tests to isolate expiry and removed an unused test import after Ruff.
- Lessons Learned:
  - Mistake: early clock sampling could become stale during lock wait; initial
    negative tests could reject for a different task/time mismatch.
  - Root Cause: admission time must follow resource acquisition, and negative
    tests need a valid control case differing only at the intended boundary.
  - Future Trigger: expiry with contention, CAS approvals or retry/replay tests.
  - Required Behavior Change: recheck time after ownership; freeze one task and
    observe the actual write-lock attempt before advancing the fixture clock.
  - Verification Step: final lock-wait test asserts the exact expiry error with
    no approval write; independent real-clock reproduction confirms behavior.
  - Durable Memory Update: recorded post-lock expiry, revision/replay and local
    account limits in project MEMORY.md.
- Known issues: account identity is not human presence. Same-account code/root
  and system clock are trusted; audit is not tamper-proof. No second-UID attack
  test or hard isolation claim. Approval records are not dispatch credentials;
  revocation does not cancel running tasks. Windows unsupported. Prior untracked
  AGENTS.md and three conflicted PID files remain preserved.
- Next recommended steps: review account authentication requirements, then define
  and test an atomic decision/revocation/submit-intent boundary with fresh runtime
  enrollment before any bounded dispatch activation. Uncertainty resolution,
  retention and broader service actions remain separate work.
- Notes for next agent: push this completed commit to its tracked branch and
  verify fetch/0/0 at closeout. Do not merge or activate based on a local approval
  record. Current master remains the approved EXTERNAL-002B integration.

## 2026-11-07 20:35 EST — Codex — EXTERNAL-003 review-only foundation

- Task/result: completed the requested EXTERNAL-002B merge and published master
  edb70433; fetch confirmed master/origin-master 0 ahead, 0 behind. Began
  EXTERNAL-003 on feat/external-003-operator-controls. Its first slice is complete;
  the broader operator-control milestone remains started. Real external actions
  and production orchestration remain disabled.
- Team: Codex lead owns scope, packet builders, integration, docs, self-review
  and Git. Luna/high was requested for bounded test implementation; effective
  worker identity is not independently exposed. Prior merge validator/reviewer
  evidence is retained. No additional native runtime or external worker pool.
- Changes/files: agent/external/operator_review.py adds pure, versioned enrollment
  and analysis task drafts; tests/test_external_operator_review.py covers their
  behavior. docs/external-003/README.md and validation.json record scope,
  evidence and ordered next work. Project MEMORY.md and this ledger updated.
- Commands/results: focused pytest 22 passed; related contract, analysis,
  Codex analysis policy and artifact verification pytest 50 passed. No skips or
  failures in final runs. Ruff F and in-memory compilation passed for both new
  files. Ten source/test hashes bind the receipt. Full merged baseline remains
  1,456 Python passes/eight Windows skips, Node39, strict renderer tsc and desktop
  build; unchanged UI/runtime source did not require another execution.
- Decisions: review packets bind caller-supplied fingerprints, claimed identity,
  normalized task/criteria and proposed authority. They are not authenticated
  approval or runtime attestation. Drift/expiry blocks drafts; invalid operations,
  wider grants and modified enrollment packets are rejected. Unsupported caller
  checks stay visible. Execution, acceptance and external-state outcomes remain
  distinct and unobserved/unverified. Existing dispatch/activation paths unchanged.
- Lessons Learned:
  - Mistake: the first delegated test draft expected blocked packets for invalid
    operations instead of the agreed ProtocolError rejection.
  - Root Cause: the tests conflated structurally invalid requests with valid
    drafts that have mismatched observations or expired authority.
  - Future Trigger: new review-packet failure cases.
  - Required Behavior Change: distinguish request rejection from blocked drafts
    when deriving tests from the contract.
  - Verification Step: corrected assertions; all 22 packet tests passed with
    no product behavior change.
  - Durable Memory Update: project MEMORY.md records drafts are not authority;
    test-authoring mismatch needs no additional durable rule.
- Known issues: authenticated operator identity, durable grant/revocation audit,
  stale approval/restart rules and dispatch integration are not implemented in
  this first slice. Broader effects require their own contracts. GitHub returned
  no status/workflow run for merged master; no remote CI pass claimed. Existing
  runtime/platform/build limits remain in the merged report.
- Next recommended steps: define authenticated operator decisions and durable
  audit; test grant/revocation, stale approvals, conflicting callers and restart
  behavior before connecting bounded analysis dispatch. Add explicit uncertainty
  resolution without native replay. Do not activate broader external actions.
- Notes for next agent: publish this branch to the same name on origin and
  verify 0/0 as final closeout; standing maintainer preference permits upstream
  setup. Preserve untracked AGENTS.md and three conflicted PID files. No native
  credentials, production configuration, memory, history or journals changed.

## 2026-11-07 20:24 EST — Codex — EXTERNAL-002B merge approval

- Task/result: completed the owner-requested merge gate for product bc88ca4b
  and its EXTERNAL-001/002 dependencies. Fast-forwarded fork master locally
  from e642eec1 through approval e5b2fca5; post-merge product hashes match.
  This completion entry is a documentation-only addition. Production activation and broader external
  actions remain disabled. EXTERNAL-003 starts on a separate branch afterward.
- Team: Codex lead owns scope, merge, docs and Git. Luna/high independently
  validated the committed evidence and activation boundaries. Reused the prior
  completed Sol engineering review; no redundant architecture review or model
  execution. Used STE branch-completion guidance within the owner's merge choice.
- Changes/files: merge-review.md, EXTERNAL-002B README status, project MEMORY.md
  and this ledger. Product source, tests and retained execution receipts unchanged.
- Commands/results: fetched origin; verified clean tracked tree, ancestor chain
  e642eec1 -> bfd64e39 -> 26c8e77d -> bc88ca4b, 78 static and nine native source
  hashes plus artifact hash; reconciled 1,464 JUnit IDs and seven exact browser
  reruns. Accepted 1,456 Python passes/eight platform skips, Node39, strict tsc,
  build/static and actual native receipts remain valid. GitHub returned no
  feature-commit status/workflow run; no remote CI pass is claimed.
- Decisions: preserve the feature branch/history. Fast-forward only; verify the
  merged source against the receipts and publish master before branching anew.
  Upstream-only image workflow conditions and manual release triggers do not
  activate this adapter on the fork. No new worker/tool registration exists.
- Lessons Learned: none. MEMORY.md records the task-specific merge authorization;
  it does not grant activation or broader effect authority.
- Known issues: retained platform/version, descendant-exit and cost-ceiling
  limits; eight Windows-only skips and existing build warnings. Untracked
  AGENTS.md and three conflicted PID files remain unrelated and preserved.
- Next recommended steps: publish and verify master synchronization; start
  EXTERNAL-003's operator review/control foundation on a
  new branch. Real external actions stay disabled pending their own contracts.
- Notes for next agent: merge approval is docs/external-002b/merge-review.md.
  Native evidence is reused because product hashes match. Do not turn merge
  approval into production activation or implicit uncertain replay.

## 2026-11-07 19:41 EST — Codex — EXTERNAL-002B bounded native supervision

- Task/result: reassessed EXTERNAL-002 on feat/external-002-codex-adapter from
  26c8e77d and implemented the real Codex analysis/artifact adapter. **READY FOR
  REVIEW** for the explicitly enrolled operation. Completed work is published
  to the same branch; no master merge or production activation is authorized.
- Team: Codex lead owns policy, contract, integration, real probes, corrections,
  evidence and Git. Luna/high researched official interfaces, mapped the
  contract, implemented deterministic analysis/verifier tests and ran release
  gates. Terra 6.1/high owned the runtime adapter and native acceptance runner;
  concurrent native lifecycle, durable state and process fixtures required more
  than routine implementation. One Sol 6.1/high reviewer handled authority and
  uncertain effects across processes. Requested models accepted; effective
  delegated identities not independently exposed. STE planning/evidence
  guidance used; no HomeBoss, nested development delegation or external
  development worker pool. Native delegation was part of the acceptance probes.
- Changes/files: new codex_adapter.py and analysis.py; explicit analyze_records
  contract extension with legacy default grants preserved; synthetic runtime
  rejects the new operation; CodexAnalysisPolicy adds read-only native policy
  and default-off tested-configuration enrollment. Three focused test files;
  docs/external-002b report, plan, review, real/regression runners, sanitized
  native/authority receipts, exact artifact/input/schema and release evidence;
  historical EXTERNAL-002 report cross-link, project MEMORY.md and this ledger.
- Native evidence: two permitted internal children mapped by public activity
  and thread parentage. Both actual negative writes (inside and outside the
  read-only workspace) reached approval and were declined; markers stayed
  absent. The old advertisement was not an escape finding. No code edit is
  required for the supervisory scenario; internal-only raw events are unused.
- Real adapter results: three native root turns in disposable Git repositories.
  Seven-record analysis returned net 13,000 cents, four accepted records and
  three correct exceptions. Actual artifact/schema/arithmetic/hash verification
  passed. Supervisor SIGKILL after runtime acceptance before host observation
  recovered the same task/session with one native turn. Fixture-only artifact
  tampering failed verification without rerun. Cancellation after observed
  reasoning first remained unconfirmed, then native interruption plus durable
  publication fence confirmed scoped cancellation. Runtime SIGTERM/restart
  preserved native IDs and no artifact/replay. Missing executable and a claimed
  unsupported effect approval were rejected. Native acceptance passed first run.
- Commands/results: opt-in native runner with /opt/homebrew/bin/codex; final
  `.venv/bin/python docs/external-002b/run_regression.py`: 1,449 pass, 15 skip,
  127 files/1,464 IDs, zero failures/errors. Seven exact browser cases passed:
  unique 1,456 pass and eight Windows-only skips. Includes 44 new cases. Node39,
  strict renderer tsc and desktop build pass; existing warnings retained.
  Fresh Ruff F/compilation pass for 10 files; 68 retained hashes match accepted
  static evidence. Initial full-run private-socket fixture failure remains
  documented; only its exact owned-socket permission was corrected, and the
  complete suite reran successfully. The retained network guard was unchanged.
- Review: three P2 findings fixed and independently confirmed by four focused
  regressions: exact profile/full config drift binding, explicit repeat cancel
  after a lost interrupt, and consistent valid artifact-name length. A timing-
  sensitive test now polls through synchronized authenticated status access.
  No remaining blocking finding for the bounded operation.
- Decisions/preservation: Codex owns model/provider/effort, instructions,
  authentication, existing memory and native sessions. No credential files read
  or copied by the adapter; no production CowAgent config/memory/history/task
  journals modified. Invocation-only project trust avoided global config writes;
  config hash remained byte-identical before/after. Fresh native fixture history
  remains native-owned. No self-evolution or new restricted-worker command tool.
- Lessons Learned:
  - Mistake: treating internal collaboration existence as a blocker, relying on
    configuration labels without effective scope checks, and overlooking the
    retained runner's established private-IPC fixture permission pattern.
  - Root Cause: runtime autonomy, authority enforcement and test transport
    isolation are different concerns. A root-turn stop also differs from task
    effect quiescence and all-descendant exit.
  - Future Trigger: external runtime enrollment, native child delegation,
    layered permission changes, lost cancellation or new IPC tests.
  - Required Behavior Change: verify public parentage and actual denied actions,
    bind full effective policy, preserve explicit cancellation repeats and exact
    fixture endpoint grants. Never infer safety from absent attempts or replays
    from verification failure. Match accepted identifiers across contract/checks.
  - Verification Step: native inside/outside child denials; config/profile drift
    tests; repeated-cancel and valid-name regressions; actual durable supervisor,
    artifact and interrupt receipts; full protected regression rerun.
  - Durable Memory Update: project MEMORY.md records the supervisory purpose,
    native autonomy, operator enrollment, scoped effects and no-replay limits.
- Known issues/limits: enrollment is specific to tested CLI 0.165.0/macOS and
  unchanged configuration; other versions/platforms require new evidence.
  All-descendant exit, provider-side compute cancellation and hard cost/resource
  ceilings are unproven. Unknown dispatch/publication remains nonterminal and
  cannot auto-reconstruct, retry or republish. Production approval UX, rotation,
  retention/queue/worker limits and external-service effects are future work.
  Existing build warnings and eight platform skips remain. Unrelated untracked
  AGENTS.md and three conflicted PID files stay excluded and preserved.
- Next recommended steps: review the bounded branch, then separately authorize
  an operator enrollment/approval and uncertainty-resolution integration. Add
  key rotation/retention and production resource controls before live use.
  Broader external effects need their own authority and independent observer.
- Notes for next agent: docs/external-002b/README.md is current. The prior
  EXTERNAL-002 report remains historical evidence. Native receipt manifests bind
  source hashes; real success and deterministic failure injection are labeled
  separately. Master remains e642eec1. Parent verifies same-name GitHub branch
  publication and 0/0 sync; do not merge or activate from this handoff alone.

## 2026-11-07 18:54 EST — Codex — EXTERNAL-002 blocked Codex runtime gate

- Task/result: integrated published EXTERNAL-001 bfd64e39 on dedicated
  feat/external-002-codex-adapter from master e642eec1. Inspected CLI 0.165.0,
  official interfaces and actual native capability events. **BLOCKED** at
  CODEX-CAPABILITY-001; no working real-adapter or release-ready claim. Publish
  the inactive foundation and evidence; no master merge or live activation.
- Team: Codex lead owns policy, probes, integration, evidence and Git. Luna/high
  researched public interfaces, tested policy and ran release gates in bounded
  assignments. Terra 6.1/high owned the stdio client because concurrent events,
  responses and process cleanup needed more than routine implementation.
  One Sol 6.1/high reviewer handled auth, permission and uncertain-effect
  boundaries across processes; that work exceeds routine Luna review.
  Requested models accepted; effective identities not independently exposed.
  Used STE design/planning guidance; no HomeBoss or external worker pool.
- Changes/files: new agent/external/codex_client.py and codex_policy.py, two
  focused test files, docs/external-002 plan/README/review/runtime receipts and
  regression runner/JSON/JUnit/output, project MEMORY.md and this ledger.
  Helpers are unregistered. No native gateway, UI, production memory/config,
  model selection, identity or instruction source changed. EXTERNAL-001
  source/evidence remains intact; its published README blob was verified.
- Results: named profile and unchanged Codex model/provider/effort confirmed.
  Explicit root/temp deny fixed the fictional command-canary boundary. Native
  patch confinement remains unverified. A real edit turn completed but left
  the file unchanged: acceptance and desired state failed. The selected model
  requires native Code Mode. Retaining that documented host exposed a separate
  collaboration advertisement despite both multi-agent flags being false.
  No collaboration call or escape was demonstrated; its origin/enforcement
  remains unknown. Stopped further real tasks under the user's blocked-gate rule.
- Commands/tests: `.venv/bin/python docs/external-002/run_regression.py` passed
  1,405, skipped 15, zero failures/errors across 124 files. Seven exact browser
  cases passed separately: 1,412 unique passes and eight Windows-only skips.
  Includes 17 new foundation and all 24 EXTERNAL-001 tests. Node suites 39 pass;
  strict renderer tsc and desktop build pass. Ruff F/in-memory compile passed
  for five new Python files; 66 retained source hashes match reused static
  evidence. Parent reconciled JUnit hash/counts and new source hashes.
- Review: independent security/architecture review confirmed the capability
  block. One P2 fixed: close now cleans same-group children after leader exit.
  Two cleanup tests passed independent narrow confirmation. No proof of
  detached-descendant termination or a complete Codex cancellation contract.
- Preservation/decisions: Codex auth remains native; no credential file read
  or copy by the supervisor. Native thread creation added only an owned fixture
  trust entry; removed that exact block after proving restoration hashes to
  the initial config. Final config hash equals the original. Native history
  was not deleted. Transport/configuration helpers do not authorize execution;
  status, execution, acceptance and independent confirmation stay separate.
- Lessons Learned:
  - Mistake: treating disabled feature metadata as proof of excluded tools;
    ordinary item events also omitted the pure Code Mode call and result.
  - Root Cause: configuration, model-facing advertisements and actual tool
    execution are different observation layers. Process leader exit likewise
    does not prove its group has exited.
  - Future Trigger: enrolling a native runtime, interpreting capability flags,
    collecting model tool evidence or cleaning up an exited process leader.
  - Required Behavior Change: inspect structured native advertisement/call/
    output records; fail closed on unproven mutation surfaces; clean owned
    groups regardless of leader state. Record native config side effects.
  - Verification Step: matched raw call/output IDs, exact artifact bytes,
    final original-config hash, same-group regression, bounded independent
    review and full applicable regression receipts.
  - Durable Memory Update: project MEMORY.md records EXTERNAL-002's blocked
    state and distinction between configuration and capability enforcement.
- Known issues: real adapter registration, durable identity/idempotency,
  uncertain replay mapping, successful code/test verification and actual
  cancellation are unfinished. Unbounded event queue, detached descendants,
  beta/version/platform limits; eight Windows-only skips and existing build
  warnings. Four unrelated untracked files remain excluded: AGENTS.md and
  three conflicted PID files. Production state remains untouched.
- Next recommended steps: establish a supported exclusion control or matching
  authoritative runtime enforcement for all advertised collaboration mutations;
  then run native patch canaries and implement/test the durable adapter mapping.
  Keep Codex auth/model unchanged. Repeat release gates and review before merge
  or activation; do not treat offline test success as closing the blocked gate.
- Notes for next agent: docs/external-002/README.md is the deployment decision.
  runtime-gates.json is sanitized evidence, not full raw transcripts. Native
  completed-history read after process restart does not prove task recovery.
  Parent publishes same-name origin branch and verifies 0/0; master stays
  e642eec1. Preserve journals, native history and all unrelated local files.

## 2026-11-07 16:10 EST — Codex — EXTERNAL-001 external runtime supervision

- Task/result: designed and validated a host-only supervisory API and one real
  synthetic process adapter on feat/external-001-runtime-contract, based on
  master e642eec1. Publish branch/evidence; no master merge, deployment, real
  external agent connection, production credential or production data access.
- Team: Codex lead owns contract/transport/supervisor/journal/verifier, process
  integration tests, schemas/docs and Git. Luna/high audited existing interfaces
  and ran release gates. Terra 6.1/high implemented the standalone fixture and
  focused tests; interacting process/effect boundaries needed more than routine
  Luna edits. One Sol 6.1/high security/architecture reviewer handled identity,
  approval and uncertain-effect reasoning across trust boundaries. Requested
  models accepted; effective runtime identities not independently exposed.
  Used STE design/planning guidance; no HomeBoss or external worker pool.
- Changes: versioned HMAC request/response contract over private Unix IPC;
  runtime-owned model/identity/session/tools/private storage; frozen operation,
  namespace and expiry grants; explicit task-hash-bound effect approval;
  additive external tables in TaskStore WAL/FULL, separate from native queue;
  durable send intent, idempotent runtime acceptance, monotonic observations;
  status-only reconciliation, explicit cancellation versus termination; native
  read-only export and fictional ledger verification independent of worker prose.
- Files: seven agent/external modules; three external suites and supervisor
  process fixture; docs/external-001 plan, README, schema, review, runner,
  JSON receipts, JUnit/output; project MEMORY.md and this ledger. Existing
  native tools, authority, memory, models and frontend source are unchanged.
- Commands/results: focused external suite 24 passed; corrected direct reused
  runner `.venv/bin/python docs/external-001/run_regression.py` passed 1,388,
  skipped 15, zero failures/errors across 122 files. Exactly retained 119-file
  selection plus three external files. Seven matching native-browser cases
  passed separately: 1,395 unique passes and eight Windows-only skips. Node
  usage/scroll/message tests 39 passed. Strict renderer tsc and desktop build
  passed. New 12-file Ruff F/compilation passed; all 54 retained source hashes
  match prior valid static evidence. Schema JSON/17 definitions/43 references
  and document links checked; no JSON Schema validator dependency added.
- Evidence: actual concurrent/duplicate socket submissions, durable nonce
  rejection, host SIGKILL before/after send, runtime SIGKILL at four effect
  boundaries, no completed/uncertain replay, one fictional effect where
  expected, requested versus confirmed cancellation, scope/approval/expiry,
  stale session/revision/identity, missing/wrong/unsupported artifact checks,
  stable runtime config/private memory/session and native queue exclusion.
  Final JUnit IDs/counts/checksum and 66 source hashes independently reconciled.
- Review: one P2 found and fixed. Prepared status queries had poisoned later
  submission by conflating transport state with send history. Separate durable
  submission_started flag now fences dispatch; actual-socket correction passed
  in the original reviewer's narrow confirmation. No other milestone blocker.
- Decisions: external runtime control stays in explicitly enrolled trusted host
  code. No restricted worker shell/network capability, global daemon, legacy
  remote bypass, real adapter or general exactly-once guarantee is introduced.
  Uncertain tasks need operator inspection; lost cancel requests need an
  explicit repeat. Human approval authentication is future integration work.
- Lessons Learned:
  - Mistake: treating transport availability as evidence of prior submission;
    also adapting a retained test guard without first proving a conflict.
  - Root Cause: independent state dimensions were conflated, and the fixture's
    existing exact-socket override was overlooked.
  - Future Trigger: status polling before submission or adding IPC tests to an
    isolated retained runner.
  - Required Behavior Change: persist send intent independently; inspect the
    fixture boundary before changing guards and reuse the runner directly.
  - Verification Step: prepare/query/submit/cancel regression and full suite
    with the final direct runpy wrapper. No extra guard patch remains.
  - Durable Memory Update: project MEMORY.md records external ownership,
    status-only reconciliation and outcome/approval limits.
- Known issues/limits: tested on macOS/APFS; eight Windows-only skips and Linux
  unverified. Existing build warnings remain. Trusted-host/local-account
  boundary, cooperative task termination, unbounded fixture retention/task
  threads, no real service observer/key rotation/approval service. Independent
  verification proves declared time-bound state only. Native restricted-mode
  and pre-fix journal limits from the prior release remain. Four unrelated
  untracked files stay excluded: AGENTS.md and the three conflicted PID files.
- Next recommended steps: none for this controlled milestone. Before real
  integration, select one adapter's official API, bind operator approval and
  key lifecycle, define service-specific deduplication/cancellation, add an
  independent effect observer, then run its target-platform failure gates.
- Notes for next agent: report is docs/external-001/README.md. Final receipts
  bind source and explicitly reuse unchanged UI/browser/static evidence where
  valid. Parent verifies remote publication and 0/0 after push; master stays
  e642eec1. Preserve journals/WAL companions; never erase uncertainty to retry.

## 2026-11-07 15:00 EST — Codex — Close renderer type gate and integrate release

- Task/result: fix the concrete ChannelsPage icon type mismatch on dedicated
  fix/channels-icon-type-contract, based on integration 1a64afad; rerun all
  release gates, publish evidence, then fast-forward release and fork master
  under the maintainer's explicit merge authorization. RELEASE READY within
  the documented restricted-mode contract. No production deployment/restart.
- Team: Codex lead owns type fix, actual rendering, evidence and Git. Luna/high
  reran Python/native-browser/static gates; a separate Luna/high reviewer
  checked the local type contract. This bounded compatibility defect needs no
  Terra/Sol architecture review. Used STE Playwright Interactive for UI checks;
  no HomeBoss or external pool. Requested models accepted; effective runtime
  model identity is not independently exposed.
- Changes: React.FC -> React.JSXElementConstructor for the numeric-size icon
  call contract; compatible with Lucide forward refs and PaperPlaneIcon.
  Product fix 9604bde7cacd19aeb914b345dcc5c9ea8616e0e4. No cast, any, ignored
  diagnostic, dependency or tsconfig change. Runtime emitted JS is identical.
- Files: ChannelsPage.tsx; desktop/tests/channel-icons-fixture.tsx; new
  docs/channel-icon-typecheck fixture, verifier, screenshots and receipts;
  issue history, integrated release README, project MEMORY.md and this ledger.
- Commands/results: strict `tsc --noEmit -p tsconfig.json` reproduced nine errors
  before the fix and passes afterward with strict=true. `npm run build` passes;
  Node usage/scroll/message suites: 39 passed. Full private release runner:
  1,364 passed, 15 skipped, 119 files. Seven exact browser skips passed separately:
  unique 1,371 passed, eight Windows-only skips, zero failures/errors. F-class
  Ruff/compilation passed for all 54 Python files; source hashes unchanged.
  Node fixture/verifier syntax and diff checks passed.
- Runtime evidence: real ChannelsPage and stylesheet in fresh Chromium context,
  synthetic read-only API; 12 card icons and 12 dropdown icons have nonempty
  geometry and expected glyphs/sizes. Both paper planes and fallback checked.
  Real clicks open/select Telegram/close. Light and settled dark screenshots
  visually inspected; no missing icons or clipping. Zero page errors; observed
  API requests were two GET /api/channels and no mutations. Owned browser and
  fixture server closed. No production backend or credentials used.
- Review: independent Luna found no blocking issue in callable compatibility,
  strictness or narrow product scope. Full orchestration review and its two
  fixes remain valid; no unrelated product code changed.
- Decisions: retain the historical failed baseline explicitly; close it with
  new passing evidence, not a waiver. All required release gates now pass.
  Publish the fix branch, then fast-forward release and master to the same
  validated tree; verify all tracking refs at 0/0 after fetch.
- Lessons Learned:
  - Mistake: expressing a JSX call contract as React.FC, which also constrains
    static validators; initial dark screenshot sampled an unfinished transition.
  - Root Cause: callable compatibility differs from component metadata, and
    class presence does not prove settled visual state.
  - Future Trigger: mixed function/forward-ref component maps or theme captures.
  - Required Behavior Change: use JSXElementConstructor for the call boundary;
    keep strict typecheck and wait for observed final colors before screenshots.
  - Verification Step: strict renderer zero errors, identical emitted JS,
    actual icon geometry/interaction and visually inspected settled captures.
  - Durable Memory Update: project MEMORY.md marks the former baseline resolved
    and retains strict renderer checking as required.
- Known issues/limits: eight Windows-only skips; Linux needs its own run.
  Existing nonfatal build warnings remain. Packaged Electron/live channel
  operations and production services were not exercised. Restricted execution,
  native-only verification and pre-fix journal inspection limits remain.
  Four unrelated untracked files stay excluded: AGENTS.md and conflicted PIDs.
- Next recommended steps: none for the requested fix and integration; any
  production deployment requires a separate controlled maintenance task.
- Notes for next agent: docs/channel-icon-typecheck/README.md is the current
  gate-closure evidence; older failed receipts remain historical. Preserve
  production state and the original SQLite repair. Final remote sync and
  published file hashes are verified by the lifecycle lead after pushing.

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
