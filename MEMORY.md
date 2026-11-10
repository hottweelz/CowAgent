# CowAgent project facts

- PERSONAL-003 extends native commitments with explicit semantic initiative,
  standing-read expiry/frequency limits and durable attention. Registered agent
  identity labels grants; the native default DB namespace remains unchanged.
  Quiet scheduled checks complete without messages. Delivery, coverage and
  attention commit together; revocation/revision checks fence final completion.
- One native tool-free streaming model call may narrow qualified news and propose
  typed source-bound decisions. It cannot create authority or new commitments.
  Proposal identity includes material event and revision; stale scope cannot be
  approved. Publication approval is a saved decision only: no connector executes
  it. Dismissal preserves outcome/history. Personal file actions remain separate.
- Owner context keeps bounded recent checks and explicitly owner/session-scoped
  conversation failures. A latest fixture or failed conversation must not be
  attributed to earlier checks. Verify model summaries against the ledger; ask
  for chronological outcomes when history is ambiguous. UI panels must leave the
  chat composer accessible in a short/narrow viewport at effective 200% zoom.

- PR #8 (BULLGOD-RESET-001) was merged normally as 1cc6ef1e on 2026-11-09.
  Its tree matched the reviewed candidate and retained local evidence. Hosted
  checks were absent, not passing. PRs #4–7 remain preserved; their deployment
  concerns do not gate the personal-agent baseline.
- PERSONAL-001 uses PersonalStore in the existing ConversationStore database
  for explicit owner goals, current accepted facts and single-use action state.
  Native agent/session identity owns records independently of model selection.
  Current personal context reloads each turn; restricted workers and guest
  speakers do not inherit it. Correction/forget affects active personal memory,
  while original transcripts and legacy memory files remain separate history.
- Personal API mutations require an authenticated console owner, an exact enabled
  profile and owned source turn. File proposals bind path/content, workspace,
  session, source and expiry. Approval and claims sample expiry after the SQLite
  writer lock; personal writes use synchronous=FULL. Claim commits before native
  permission-gateway/FileBroker effects. Unknown/failed/completed actions never
  replay automatically. UI request generations prevent stale reads or mutations
  from restoring old facts or acting in a switched conversation.
- The isolated developer launcher can opt in to one explicit loopback model
  gateway. Its runtime bootstrap removes the transient credential environment
  variable and supplies authorization only to that gateway's HTTP headers; the
  value is not in application config, command arguments or instance files. The
  default still denies outbound traffic. BullGod's starter persona is stored in
  its own AGENT.md. No production OAuth token or authority record is copied.

- PERSONAL-002 adds owner-confirmed commitments in the existing ConversationStore
  DB, independent of PERSONAL-001 goals. Native owner/origin/source checks guard
  intent changes. Exact approved HTTPS reads use an issued host context through
  the existing permission gateway; ordinary models, guests and restricted workers
  do not inherit it. Read grants never authorize publication. Saved drafts remain
  awaiting publication approval and retain delivered-source provenance.
- Commitment run claims and occurrence uniqueness are durable SQLite state.
  Delivery, seen/selected sources and the native assistant message commit together.
  Failed/uncertain runs are not successful deliveries; expired claims require
  explicit owner acknowledgment before fresh execution. Typed pointers reuse the
  native scheduler, reject stale revisions and recheck current intent. Native
  catch-up is ten minutes; older slots skip forward. TaskStore retains its existing
  single-process coordination contract; no multi-host scheduler is introduced.
- Personal article coverage uses stable source/URL identity, owner-topic lexical
  filtering and conservative event grouping. A source URL/publisher/headline are
  required for selection. Dates alone are not updates; localized substantive
  additions can be updates even in long bodies. Preserve source snapshots for
  follow-ups/drafts beyond the recent-run window; expose earlier delivered stories
  in the draft picker. Model summaries can be wrong and do not override run state.
- Isolated approved online reads use explicit public-address pins with verified
  HTTPS names. On macOS the app reaches only an owned fixed-destination loopback
  relay plus its selected model gateway. The relay does no TLS termination, URL
  routing or arbitrary CONNECT. Refresh pins only through explicit new isolated
  configuration. Keep live-fetch evidence distinct from labeled timing/payload
  fixtures; stop owned processes and restore fixture bootstrap after acceptance.

- BULLGOD-RESET-001 refocuses development on BullGod as a persistent personal
  agent. Identity, inspectable/correctable memory, owner commitments and useful
  permission-aware follow-through come before optional specialist delegation.
  Use existing registry/workspace/session/memory/tool/model mechanisms; worker
  recovery records are not owner goals. Initial product milestones are only
  PERSONAL-001 through PERSONAL-004 in docs/bullgod-reset-001/README.md.
- FIRST-BOOTSTRAP-001/002 are completed investigations. Their unresolved ingress,
  interruption and private-recovery concerns remain deployment risks, not gates
  for personal-agent development. PRs #4–7 and their evidence are preserved;
  startup/drain/migration/plugin-certification work is deferred. Do not resume
  legacy PID retrofit, unavailable-runner investigation or repeated ownership
  audits without a new concrete maintainer request.
- The clean reset branch starts at stable master and extracts only independent
  filesystem/read-only-journal safeguards, supplied-settings discovery routing
  and an audio fixture correction. Read-only journal views cannot acquire
  execution locks. No authority/approval or broader discovery execution is added.
- scripts/bullgod_dev.py provides a separate macOS development instance with an
  explicitly selected virtual-environment Python, private source/data/workspace,
  synthetic BullGod identity, disposable console authentication and default-deny
  sandbox. No production credentials/approvals/memory are copied; provider network
  is disabled and agent permissions start read-only. Reuse a root for restart
  continuity; create a fresh root for reset. Temporary storage is not production
  persistence. Stage new application files before taking a tracked source copy.

- BULLGOD-DISCOVERY-001 was integrated through PR #3 at merge 40958f39 after
  focused integration review and passing automatic master CI. It adds the internal `agent.discovery` derived view over
  AgentRegistry and existing enrolled ExternalSupervisor bindings. It has no
  identity database or dispatch method. Strict task requirements and versioned
  policy filter before deterministic preference/load/model/ID ranking. Every
  selection remains dispatch_permitted=false and requires current executor
  admission. Missing trusted proof/admission readers fail closed; synthetic
  acceptance does not certify current live targets. Explicit host observations
  expire within 30 seconds; discovery never starts a probe or reserves a slot.
  Existing adapters remain analyze_records-only. Persistent named execution has
  owned native context and a fresh session; isolated delegation has no persistent
  target memory. See [BULLGOD-DISCOVERY-001](docs/bullgod-discovery-001/README.md).

- INFRA-RELIABILITY-001B verified the owner's removal of
  `/Volumes/Predator SSD GM7 1TB/Projects` from pCloud Backup on 2026-11-08.
  No remaining configured Backup or Sync root overlaps the checkout, `.git`,
  COW_DATA_DIR or agent workspaces. This supersedes Git metadata migration;
  keep existing paths/worktrees. Recheck actual Backup and Sync mappings if
  conflicts recur: being outside the pCloud mount alone does not establish
  isolation. Configuration evidence is not a kernel watch inventory. The
  historical ref writer remains unidentified; preserve recovery artifacts.
- The integrated ordinary CI uses `scripts/ci_test.py` with a
  prepared absolute TIKTOKEN_CACHE_DIR and temporary HOME/data. It clears inherited
  model settings and guards Python connections to owned fixtures, excluding9899.
  This does not confine native/subprocess networking. Native agents/models and
  production state stay outside ordinary CI. `scripts/git_ref_watch.py` is a
  bounded read-only detector, not writer attribution or automatic repair.
- A recovery worker can finish timed_out before the parent pool deadline. The
  subagent result must carry a timeout diagnostic before its state callback and
  UI closure; preserve a more specific existing error.

- Operator journal privacy checks recheck only otherwise-private regular
  SQLite sidecars whose transient link count is zero during unlink. Missing
  sidecars or valid replacements are allowed; unsafe or persistently zero-link
  entries and zero-link primary databases remain denied. This handles concurrent
  connection cleanup without weakening owner, mode, symlink or hardlink checks.

- Guest sharing accepts only supported exact wrapper/native tool pairs with
  the configured path/write shape and an exact GuestAgent/tool/work-root binding.
  PathGuard maps virtual paths before the native permission gateway; restricted
  filesystem calls still use FileBroker. Restricted privileged tools, unknown
  tools, MCP execution and legacy remote invocation remain denied. See the
  [integrated routing review](docs/agent-routing-003/merge-review.md).
- Full local regression uses directory-mode `pytest tests/` collection. A
  programmatic runner on macOS must be file-backed with a main guard for spawn.
  Put the selected virtual environment first on PATH for subprocess fixtures.
  Optional parser coverage needs the document packages in
  `requirements-optional.txt`; native browser fixtures use separate temporary
  profiles and require `COW_BROWSER_NATIVE_TEST=1`. Windows checks require Windows.
  Container gates need a disposable writable checkout and non-root user, process
  tools/init, and cached tokenizer assets before network isolation. The FTS5
  integrity fixture assumes SQLite 3.44 or newer. Keep SQLite fault injection
  scoped to the fixture DB; keep subprocess readiness outside buffered text
  reads when later using communicate().

- AGENT-ROUTING-003 extends the persistent named-agent adapter to `testpilot`
  and `testpilot2`. Each endpoint has one enrolled registered identity and a
  credential runtime ID of `cowagent.<agent_id>`. The task cannot override the
  target. Each native process retains its receiver's profile, native prompt,
  configured model and memory manager. Same-runtime execution is serialized;
  two separately enrolled target processes were observed to overlap safely in
  the bounded fictional analysis acceptance. No persistent activation occurred.
- Native preflight rejects overlapping supported workspaces, memory DB paths
  outside their owning workspace and shared DB inodes before initialization.
  Actual memory-manager workspace/configured/opened DB paths must match after
  initialization. Receipts carry public identity, model/provider, profile hash,
  opaque memory-scope hash and native session/run/process/timing metadata.
  Preflight permits settled recovery history but blocks queued/running tasks
  and completed tasks missing current-attempt verification. See
  [AGENT-ROUTING-003](docs/agent-routing-003/README.md).
- Tests that enter the real tool permission gateway need a valid Agent authority
  context and an exact registered tool descriptor. The parallel-tool fixtures
  use a read-only session and stub only registered SubagentTool execution;
  `agent=None` and unregistered toy tools do not test authorized scheduling.

- AGENT-ROUTING-002 audited the existing live supervisor delegating to both
  `testpilot` and `testpilot2`. Both restricted native tasks completed once in
  sequence with correct fictional calculations, but each claimed `CowAgent` in
  its output. Target identity must come from native task/peer metadata, not the
  model's self-name. Neither child loaded persistent receiver context or memory.
  BullGod should expose restricted native delegation and approved persistent
  named-agent invocation as distinct mechanisms. This audit did not extend the
  then TestPilot-only enrollment; AGENT-ROUTING-003 adds TestPilot2. See
  [AGENT-ROUTING-002](docs/agent-routing-002/README.md).
- Native conversation tables reside in the default memory index and are scoped
  by `agent_id`; receiver memory indexes are not separate conversation stores.
  Delegation display runs belong to the source session. Use the task journal's
  target identity and session plus native peer events when checking routing.

- AGENT-ROUTING-001 adds an opt-in Codex-to-CowAgent named-agent experiment for
  registered `testpilot`. The persistent native `get_agent`/`run_stream` path
  preserves registered instructions, profile model inheritance and native
  memory ownership; existing `agent_delegate` remains a separate restricted,
  memory-less worker path. Do not treat them as interchangeable.
- The named adapter reuses private authenticated IPC, atomic operator approval
  and intent gates, and independent analysis verification. Its strict enrollment
  binds the selected `testpilot` or `testpilot2`, config/profile/source and
  model/provider fingerprints.
  Only fixed fictional `analyze_records` tasks are supported. Server-owned fresh
  sessions use native read-only permission without generic worker authority.
  Exact result equality gates publication so arbitrary private output cannot
  pass through schema-valid strings. Uncertain attempts never replay.
- Native startup preflight checks scheduler primary/backup stores, recovery work,
  evolution, MCP files/config, target onboarding and credential synchronization.
  Read-only task authority does not prohibit native index/bookkeeping writes.
  Caller Python-open instrumentation is not OS confinement. The controlled
  experiment passed with one real TestPilot run; no persistent service or broader
  production activation is authorized. See [AGENT-ROUTING-001](docs/agent-routing-001/README.md).

- Maintainer preference (2026-11-07): push completed task commits for tracking.
  Publish new CowAgent task branches to the same branch name on the existing
  `origin` fork (`hottweelz/CowAgent`) and establish upstream tracking without
  another confirmation. This overrides the default no-upstream stop for this
  known fork. Verify synchronization after pushing. Merges and deployments
  retain their separate task-specific authorization.
- Worker authorization is a trusted-host capability boundary, not an OS sandbox.
  Restricted workers cannot execute Bash, arbitrary programs, browser or MCP
  calls. Native text-file operations use a descriptor-relative POSIX broker.
- Temporary workers have fresh task directories and explicit optional shared
  roots. Local delegation intersects caller and receiver authority and retains
  both sides' private-state exclusions. It does not load a persistent receiver's
  private memory, skills or conversation history.
- Remote peer invocation and legacy scheduled tool calls are unsupported until
  they carry enforceable task authority. Existing explicit full-access owner
  sessions retain known native host tools; unknown tools fail closed.
- The detailed contract, compatibility limits, threat model and validation are
  in [ISOLATION-001](docs/isolation-001/README.md).
- Native temporary workers and local delegation use a separate private WAL/FULL
  journal at shared_root()/memory/recovery/tasks.db. Task and attempt IDs are
  separate; POSIX task locks and receiver/session locks stay held while a live
  worker remains active. Stops, completion and tool receipts are attempt-fenced.
- Abandoned tasks restart from frozen input only if that attempt has no mutating
  tool intent. Otherwise an operator must inspect and explicitly acknowledge
  retry; completed tasks never replay. Current grants can only narrow frozen
  authority. The [RECOVERY-001 guide](docs/recovery-001/README.md) defines the
  operator commands and limits; this is not chat/scheduler continuation or an
  exactly-once effect guarantee. Keep the journal outside file-sync conflict
  handlers, like the memory index.
- Worker execution, acceptance and independent state confirmation are separate
  outcomes. Completed execution stays non-replayable when acceptance fails.
  Caller criteria are frozen before dispatch; native read-only text/JSON checks
  append attempt/contract-bound reports. Missing or unsupported checks remain
  unverified. Restart can finish verification without rerunning the worker.
  [VERIFICATION-001](docs/verification-001/README.md) defines check syntax and
  limits; native filesystem confirmation does not certify remote-service state.
- Conversation ownership and execution identity are distinct. A guest's durable
  subagent keeps the guest profile/model and the host-owned journal/session
  grants. Recovery rechecks host roster membership and current permissions.
  Explicit retry advances a journal generation; old waiters cannot claim or
  stop a replacement generation. Preserve stopped-attempt snapshots when a
  retry races the result. See the integrated
  [release assessment](docs/orchestration-release-001/README.md).
- SQLite indexed-memory/WAL behavior and EFFICIENCY-001 Phases 1–4 remain covered
  by integrated regressions. The former nine ChannelsPage errors are resolved
  by the JSX component call contract; strict renderer typecheck is a required
  passing gate. The [issue history](docs/known-issues/channels-page-typecheck.md)
  preserves the failed baseline and links the verified correction.
- EXTERNAL-001 provides an opt-in trusted-host supervisory API and a synthetic
  external runtime over authenticated private Unix IPC. It does not install a
  native worker tool or enable legacy remote invocation. External runtime
  identity, model, sessions, credentials, memory and tools remain runtime-owned.
- External records use additive external_* tables in the existing WAL/FULL task
  journal, never the native dispatch queue. Durable submission intent is separate
  from transport availability. Uncertain sends reconcile by status only; they
  never automatically resubmit. Cancellation intent is separate from confirmed
  termination; lost cancellation requires an explicit repeat. Independent export
  and synthetic ledger checks certify only declared, time-bound state. Real
  adapters need separate runtime evidence; human approval authentication and
  remote-effect verifiers remain future work. See [EXTERNAL-001](docs/external-001/README.md) for the contract,
  failure rules, test evidence and limits; no general exactly-once claim applies.
- The fork's external-agent direction is supervisory: a potential BullGod
  component delegates bounded tasks and verifies outcomes while independent
  runtimes own their models, authentication, instructions, memory and workers.
  Internal delegation is acceptable within inherited task authority.
- EXTERNAL-002B supersedes EXTERNAL-002's historical blocker for explicitly
  enrolled native read-only analysis. Actual public child lineage and declined
  inside/outside writes established the observed native delegation boundary;
  an advertised collaboration tool alone proves neither escape nor safety.
- The opt-in Codex adapter uses authenticated private Unix IPC and public
  app-server stdio. `analyze_records` accepts bounded data, returns structured
  JSON, and permits only supervisor-controlled artifact publication. Enrollment
  binds tested CLI/model/provider, policy/probe digest, full configuration and
  provider hashes, plus fresh exact effective profile checks. Native config and
  model selection are not rewritten. Internal-only raw events are not used.
- Codex submission and publication intents are durable; uncertainty never causes
  automatic replay or republishing. Cancellation fences publication before
  interrupt; explicit repeats can recover lost interruption. Scoped task-effect
  confirmation is distinct from all-descendant exit or a hard cost ceiling.
  Independent analysis and caller criteria must pass before verification is
  claimed. [EXTERNAL-002B](docs/external-002b/README.md) records passing real and
  fixture tests, supported enrollment and limits. The owner-authorized
  EXTERNAL-002B master integration is complete. The owner-approved EXTERNAL-003
  and EXTERNAL-003B consolidation adds local approvals and enforced dispatch.
  Production activation and broader effects remain unauthorized.
- EXTERNAL-003 begins with pure `cow.external.operator-review/1` enrollment and
  bounded-analysis task drafts. Fingerprints bind supplied observations, task,
  proposed authority and criteria; they do not authenticate an operator or
  prove fresh runtime state. Drafts never grant approval or enable execution.
  The explicit local operator CLI now derives the account from real/effective
  UID and records enrollment/task approval/revocation in a private WAL/FULL
  operator journal. Scope/spec hashes, expected revisions, enrollment revision
  and expiry bind decisions; exact replays return historical receipts plus
  current state without regranting. Audit preserves decision snapshots. Expiry
  is checked after writer-lock acquisition; state ancestors must be trusted.
  This authenticates a local account, not human presence; same-account code,
  root and the system clock are trusted. The standalone CLI never dispatches
  work. Explicit dispatch integration is provided by EXTERNAL-003B below; owner
  review is still required before production activation. See
  [EXTERNAL-003](docs/external-003/README.md). Real external actions remain disabled
  pending separately tested authority and verification contracts and activation
  authorization.
- EXTERNAL-003B uses ApprovalJournal to colocate operator decisions and external
  task/send/native/publication intents in one private operator.db WAL/FULL
  journal. Each one-shot admission checks current identity/spec, credential,
  approval/enrollment revisions and post-lock expiry in the same transaction.
  Native admission follows fresh Codex attestation. Generic/ungated analysis
  submissions and claimed approval labels fail closed; only analyze_records is
  available through the real adapter (cow.codex/2).
- Operator revocation/replacement atomically fences bound tasks and queues
  cancellation. Runtime polling and supervisor delivery share one claim;
  unknown delivery requires explicit cancel retry. Reconciliation may deliver
  that already-requested cancellation once, but never resubmits a task or
  republishes an artifact. Revocation after native/publication intent commit
  cannot retract that authorization. Adapter restart has no live native client
  for interruption; cancellation intent is not termination proof.
- EXTERNAL-003B's actual Codex acceptance passed with two delegated model turns,
  operator revocation, host/native-intent crash recovery and independent artifact
  verification. Empty native-thread history returned thread-not-loaded; this is
  recorded as unavailable, with separate outbound RPC evidence, not as empty
  public history. The [report](docs/external-003b/README.md) records evidence and
  limits. The maintainer authorized master consolidation after merge review;
  production activation and broader service actions remain unauthorized.
- MemoryStorage.close() closes the foreground connection without joining
  asynchronous maintenance. Disposable shared-database fixtures must wait for
  maintenance before unlinking the database or removing its directory. Deletion
  during the background open reproduces SQLITE_IOERR_FSTAT (1802) at the WAL
  pragma on SQLite 3.45.3. The shared-db test teardown enforces this ordering
  and retains the database if its bounded wait fails. See the
  [diagnostic investigation](docs/external-003b/sqlite-diagnostic.md); this is
  distinct from the earlier renamed-WAL SQLITE_IOERR_SHORT_READ (522).
