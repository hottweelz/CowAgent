# CowAgent project facts

- AGENT-ROUTING-002 audited the existing live supervisor delegating to both
  `testpilot` and `testpilot2`. Both restricted native tasks completed once in
  sequence with correct fictional calculations, but each claimed `CowAgent` in
  its output. Target identity must come from native task/peer metadata, not the
  model's self-name. Neither child loaded persistent receiver context or memory.
  BullGod should expose restricted native delegation and approved persistent
  named-agent invocation as distinct mechanisms. The 001 adapter remains scoped
  to TestPilot; this audit did not extend enrollment. See
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
  binds `testpilot`, config/profile/source and model/provider fingerprints.
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
