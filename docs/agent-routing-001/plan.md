# AGENT-ROUTING-001

Goal: Codex delegates a fixed fictional read-only analysis to the existing
registered `testpilot`, preserving its native instructions, model selection,
workspace memory and runtime execution.

1. Trace manual chat through retained routing logs and current source. Read
   registry/model metadata only; do not open private memory or history in Codex.
2. Distinguish the persistent native route from `agent_delegate`, whose generic
   restricted child intentionally omits receiver context. Use the former.
3. Reuse `ExternalTransport`, `ExternalSupervisor`, `ApprovalJournal` and the
   analysis verifier. Add a strict named CowAgent enrollment and an opt-in local
   runtime adapter. Keep the general chat API disabled.
4. Resolve a fresh server-owned session through native `AgentBridge.get_agent`,
   enter receiver runtime identity, and use native read-only permission. Pass
   caller attribution and fixed records as user content. Do not set a replacement
   system prompt, model override, generic worker authority or transcript.
5. Gate native/publication intents on current approval and enrollment. Never
   replay a submitted attempt after a duplicate request, crash or lost reply.
   Publish only a report equal to the frozen expected result. Independently
   verify the exported artifact afterward.
6. Run focused unit/contract checks, one real authenticated task and an independent
   source/evidence review. Bind receipts to current source. Record any limitation.

Team: Codex lead owns native entry point, enrollment, real acceptance, docs and
Git. Luna/high maps manual routing and contracts and tests enrollment. Terra
6.1/high owns the adapter and its tests because admission, cancellation and
recovery interact across transactions. Sol 6.1/high reviews the private-memory
and concurrent authority boundary. Requested model settings are accepted by the
runtime; effective delegated model identities are not independently exposed.

Existing lessons applied: sample expiry after transaction lock (reuse admission
gate); preserve unknown execution rather than replay; keep memory databases
alive until asynchronous native work ends; reuse valid focused evidence.

Native startup preflight rejects unrelated scheduler/recovery work, enabled
evolution, MCP configuration, incomplete onboarding and credential synchronization.
Native memory/index maintenance is still native-owned: read-only describes the
task's tool authority, not a promise of no runtime bookkeeping writes.

No broad service activation, generic remote delegation, model changes or new
orchestration platform is in scope. Branch: `codex/agent-routing-001` from
`master` at `9cd8c535`. Existing untracked AGENTS.md and conflicted PID files stay
outside the task commit.
