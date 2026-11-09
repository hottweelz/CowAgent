# BULLGOD-DISCOVERY-001 architecture decision

Baseline: master `0805c82ef55342b105c835cee77c21d6e385c434`.
Scope: internal discovery, deterministic eligibility and selection. No dispatch,
live model tasks, public endpoint, scheduler or production activation.

## Decision

Build a derived view of `AgentRegistry` and explicitly supplied existing enrolled
external-supervisor bindings. Resolve identities afresh through their authority
source; never create a second roster. Keep the three mechanisms separate even
when they have the same target or task category.

Use strict versioned task and policy contracts. Eligibility precedes ranking.
Unknown or stale capability, authority, health or admission facts cannot grant
eligibility. Natural-language descriptions are display declarations only. All
discovery output is an allowlisted public projection; no prompt, task text,
credential, memory content, filesystem root or raw exception is returned.

Selection records carry task, policy, identity, configuration and evidence
fingerprints. They are explanations, not approval credentials. Revalidation
rebuilds current state; the existing execution admission must still run. No
selection result can bypass an operator revision, revocation or changed task.

## Source-of-truth map

| Field or boundary | Existing source | Interpretation |
| --- | --- | --- |
| Native ID/name/enabled/profile | `agent/registry.py:AgentRegistry` / `AgentProfile` | Authoritative identity; role text does not prove specialty |
| Current roster | Strict `agent/permission/authority.py:_current_registry` | Corrupt roster fails closed; avoid permissive UI fallback |
| Native team/ACL/cycle/depth | `agent/tools/agent_delegate/agent_delegate.py` and `agent/recovery/runtime.py` | Current caller-turn checks, not global profile permissions |
| Restricted tools and grants | `agent/permission/authority.py`, native worker tool allowlist | Intersect caller/receiver authority; do not export roots |
| Native model inheritance | `AgentLLMModel.set_agent_default` and frozen recovery model reference | Accurate trusted route or unknown; never a quality score |
| Persistent identity | Native registry plus `cowagent.<id>` credential and named-adapter enrollment | Only testpilot/testpilot2 supported by current adapter |
| External identity | Existing `ExternalSupervisor.transport.credential` binding | Runtime-owned identity; not a CowAgent persistent profile |
| Current approvals/revocation | `OperatorControl.status` / operator decision audit | Exact owner/source/conversation/runtime scope and revisions |
| Task binding and one-shot admission | `ApprovalJournal`, `normalize_spec` and spec digest | Discovery must not create or consume an intent |
| Verified enrollment | Approved operator enrollment plus current matching executable/config/probe evidence | A review packet alone is caller-supplied, not proof |
| Runtime observation | Existing authenticated external wire envelope and explicit trusted host observation | Freshness-bound; no implicit live probe in selection |
| Independent analysis verification | `agent/external/analysis.py` and verifier | Fixed fictional-record schema and exact expected result |
| Native artifact verification | `agent/recovery/verification.py` | Read-only local checks; remote state unsupported |
| Cancellation/recovery | Existing native/external journals and adapter code | Cooperative/scoped; no exactly-once or all-descendants guarantee |

## Mechanism semantics

`native_isolated` uses existing `agent_delegate`: generic restricted worker,
no persistent target memory manager, skills, context files or conversation
history. Selecting a registered ID does not change those semantics.

`persistent_named` uses the authenticated CowAgent adapter: native receiver
profile/context/memory ownership and a fresh server-owned task session. This is
not restoration of prior manual chat. Each enrolled runtime serializes native
work; separate runtime boundaries do not prove model-provider parallelism.

`external_runtime` retains external identity, provider/model authentication,
task contract, enrollment, approval and independently verified effects.

Both real adapters currently support only `analyze_records`. The Codex adapter
does not support arbitrary coding. Scenario C must deny an external development
task under the current contract; its name does not supply coding authority.

## Alternatives rejected

- A second BullGod identity/evidence registry would drift from native identity
  and operator revocation. Use a derived snapshot instead.
- Calling existing adapter `discover()` on every selection would hide side
  effects: Codex discovery can create a directory and start a native process.
  Require explicit current evidence through a trusted integration boundary.
- Ranking natural-language role claims or guessed model costs would elevate
  declarations into permission. Use explicit known facts and stable tie breaks.

## Implementation and verification plan

1. Lead preserves baseline, pCloud scope, existing worktree/recovery/untracked
   files and runtime metadata; creates the requested feature branch.
2. Core worker implements `agent/discovery/` strict contracts, derived sources,
   eligibility, ranking, freshness and revalidation. Existing source changes are
   limited to necessary backward-compatible read-only hooks.
3. Separate acceptance tests cover A-I plus identity spoofing, untrusted proof,
   revocation/config/policy/task drift, expired health, permissions and privacy.
   Use disposable existing registry/operator journals and synthetic evidence;
   forbid model tasks and verify no dispatch/approval/intent mutation.
4. Run focused new tests and affected adapter/native compatibility tests. Obtain
   one independent high-reasoning authority review; repair concrete findings.
5. Publish a draft PR and run the existing hosted macOS/Linux matrix, JavaScript,
   strict TypeScript, build and Ruff. Reconcile source-bound receipts. Update
   report and handoff, push and verify 0 ahead / 0 behind. Do not merge.

No live registration, model configuration, credential, profile or memory changes
are part of this design. Missing evidence remains a sanitized reason for refusal.
