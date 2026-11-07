# CowAgent project facts

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
  by integrated regressions. The nine ChannelsPage typecheck errors are a
  [separate baseline defect](docs/known-issues/channels-page-typecheck.md).
