# CowAgent project facts

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
- SQLite indexed-memory/WAL behavior and EFFICIENCY-001 Phases 1–4 remain covered
  by integrated regressions. The nine ChannelsPage typecheck errors are a
  [separate baseline defect](docs/known-issues/channels-page-typecheck.md).
