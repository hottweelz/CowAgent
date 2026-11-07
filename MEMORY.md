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
- SQLite indexed-memory/WAL behavior and EFFICIENCY-001 Phases 1–4 remain covered
  by integrated regressions. The nine ChannelsPage typecheck errors are a
  [separate baseline defect](docs/known-issues/channels-page-typecheck.md).
