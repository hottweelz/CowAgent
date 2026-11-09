# BULLGOD-DISCOVERY-001

Internal capability discovery, deterministic eligibility and selection. Baseline:
`0805c82ef55342b105c835cee77c21d6e385c434`. Branch:
`codex/bullgod-discovery-001`. This milestone does not activate BullGod or dispatch
work. DISCOVERY-002 Gate A subsequently authorized integration: PR #3 merged as
`40958f392bca59009224fcebfd1b636a861615ab`; automatic master CI passed. See the
[integration report](integration.md).

**PASSED** for this development milestone. Focused validation, independent review
and all five hosted CI jobs pass on source
`ff09850d089622bd9dca30508b0ce03d21cbcdb4`.
The [hosted receipt](hosted-validation.json) reconciles logs, JUnit cases, skips
and the exact checked-out source tree.
[Merged PR #3](https://github.com/hottweelz/CowAgent/pull/3) publishes the work.

## Architecture and authoritative state

The [architecture decision](architecture.md) maps existing source files to each
field and boundary. `agent.discovery` derives candidates from the current strict
`AgentRegistry` and existing `ExternalSupervisor` bindings. It stores no second
roster, credentials, approvals, memory, task queue or persistent capability cache.

Native identity, enabled state and profile hashes come from the registry. Native
team membership, source identity, depth, cycle, delegation policy and intersected
authority come from the current caller turn and the existing permission code.
Model inheritance uses the existing model routing methods without constructing
an Agent, memory manager, model client or worker.

External identity comes from each existing supervisor's credential and caller
scope. Persistent adapters also require the matching native registered identity.
The read-only `ApprovalJournal.preview_admission()` inspects exact task/spec,
credential, current enrollment/task revisions, expiry, cancellation and prior
submission intent in one transaction. Actual execution still uses the existing
admission transactions. A discovery result is never an approval credential.

Discovery does not call a transport's `discover()` method. Such a call can start
an external process. The host supplies a retained authenticated discover response
from a separately authorized observation. The response must match current
enrollment and profile evidence. Missing or stale observations fail closed.

## Contracts

The executable schemas are frozen dataclasses in
[`contracts.py`](../../agent/discovery/contracts.py). JSON requirements reject
unknown keys, unsupported enum values, duplicate lists, malformed identifiers,
nonfinite times and inconsistent constraints. Task metadata has no instruction,
credential, file-root or permission-grant field.

| Contract | Version | Contents |
| --- | --- | --- |
| Decision | `cow.discovery/1` | Status, candidates, selected target/mechanism, reasons, ranking, hashes, freshness, sanitized audit |
| Requirements | `cow.discovery.task/1` | Exact fields below; strict `TaskRequirements.from_dict()` boundary |
| Capability | `cow.discovery.capability/1` | Categories, input/output contracts, tool classes, verification, recovery, cancellation, tested timeout ceiling |
| Policy | `cow.discovery.policy/1` | Policy ID/revision and ordered target/model preferences |

Required task fields:

| Fields | Meaning |
| --- | --- |
| `task_id`, `policy_id`, `task_spec_hash` | UUID, configured policy and trusted task digest |
| `category`, `input_contract`, `output_contract` | Exact machine-readable compatibility |
| `persistent_memory` | `required`, `prohibited` or `optional` |
| `required_tools`, `max_authority` | Required tool classes and upper authority bound; no new grants |
| `approval` | `required`, `optional` or `prohibited` |
| `verification` | `none`, `native_checks` or `independent_analysis` |
| `recovery` | `none`, `frozen_authority` or `intent_fenced` |
| `cancellation` | `none` or `cooperative` |
| `deadline`, `timeout_seconds`, `concurrency` | Absolute deadline, maximum supported execution budget and required slots |
| `permitted_mechanisms`, `prohibited_mechanisms` | Explicit mechanism constraints |

Optional fields are `persistent_context` (same three values as memory, default
`optional`), `model`, `provider`, `requested_agent_id` and `protocol`. Model IDs
allow bounded provider-qualified names; raw paths, URLs and controls are rejected.
The supported authority classes are `fs.read`, `fs.write`, `time` and
`analyze_records`. A requested class never creates an underlying grant.

The complete external spec remains outside task metadata. Its selection digest
is computed by `task_spec_fingerprint(spec)`, which omits only `runtime_id` from
the normalized spec. This permits comparison across targets. Each target still
requires its exact full spec, credential, caller scope and operator approval.
Changing task content, resources, authority, identity scope or verification
criteria invalidates the binding.

`CapabilityContract` is a declaration. `CapabilityProof` adds a current
configuration fingerprint, evidence fingerprint, issue/expiry times and
`trusted_test` or `approved_enrollment` provenance. `AdmissionObservation` adds
the specific admission-boundary fingerprint, health, available slots, optional
known load and issue/expiry times. These are **trusted host inputs**, not
model-facing JSON and not evidence merely because a caller constructs the type.
The host must authenticate and validate the underlying receipt before supplying
them. No production proof or admission provider is installed by this milestone.

The public projection separates `declared_capabilities`, `verified_capabilities`,
`verification_status`, health and `eligible_for_admission`. Display names use safe
registered IDs, and roles use fixed identity classifications; private profile
prose is not exported. Paths, instructions, memory and credentials remain private.

## Execution mechanisms

| Mechanism | Identity and context | Existing admission and limits |
| --- | --- | --- |
| `native_isolated` | Registered target; generic restricted worker; no persistent target memory, skills, context files or conversation history | Current caller team/policy/authority and native recovery; one observed receiver/session slot; cooperative cancellation |
| `persistent_named` | `testpilot` or `testpilot2`; native profile, skills and owned memory; fresh server-owned task session | Separate `cowagent.<id>` credential/enrollment/task approval; one task per runtime; independent analysis and durable intent fences |
| `external_runtime` | Existing external runtime such as `codex`; independent model/authentication/context ownership | Exact enrolled contract, task approval, independent analysis and durable intent fences; admission from the runtime's own boundary |

Persistent invocation does not restore a previous manual transcript. External
context semantics are unknown for the supported adapter, so it cannot satisfy an
explicit native-memory requirement or a prohibition of persistent context.
Separate persistent admission boundaries do not prove model-provider parallelism.

Both real external adapters currently support **only `analyze_records`** with
`fictional_records.v1` input and `analysis_report.v1` output. A name such as Codex
does not grant coding, shell or general network authority. No separately verified
stateless mode exists for these adapters.

## Eligibility, ranking and selection

Eligibility checks authoritative identity/enabled state; mechanism and exact
capability contracts; current proof; effective authority and required tools;
model/provider constraints; current enrollment/approval; health and admission;
memory/context semantics; verification/recovery/cancellation; task budget; and
native team, cycle and depth limits. Unknown, unavailable or ambiguous state
cannot grant permission. Missing/expired task approval returns `approval_required`
only when that is the remaining barrier; denied/revoked authority remains denied.

The execution budget must fit both the caller maximum/deadline and the verified
capability ceiling. Native budget comes from actual delegation policy. For the
existing external adapters it is the earliest credential, task authority,
enrollment or task approval expiry. This is a conservative effect/cancellation
fence, not proof of hard process exit or a cost ceiling. Discovery never rewrites
the adapter's timeout or approval expiry to make a candidate qualify.

Only eligible candidates are ranked, in this fixed order:

1. Operator-configured target preference.
2. Known load before unknown load, then lower known load.
3. Configured model preference.
4. Stable target ID and mechanism tie-breaks.

The policy version and preferences are fingerprinted. Capability, context and
verification requirements are eligibility gates, not tradeable scores. There are
no guessed cost, quality, latency or throughput weights. Candidate enumeration
order cannot change the selected target. An explicit persistent target denial
cannot fall back to another mechanism for that target unless the task explicitly
prohibits persistent memory and thus requests a different mode.

`DiscoveryService.discover(task)` and `.select(task)` return the same evaluated
view; `.mechanisms()` lists mechanism names. Status is `selected`,
`approval_required`, `denied` or `invalid_request`. Results include rejected
alternatives, sanitized reason codes, ranking rationale and task/policy/identity/
configuration/evidence/state fingerprints. **Every result has
`dispatch_permitted: false` and `execution_revalidation_required: true`.**

## Lifecycle, audit and future Luna integration

1. Register identities only through the existing registry or external enrollment.
2. Supply operator-controlled structured declarations bound to that identity.
3. Verify an exact capability under source/configuration/profile/model/contract
   fingerprints. Supply authenticated evidence through the trusted host boundary.
4. Read current enrollment/approval and bounded health/admission observations.
   Admission age and lifetime must each remain below/at the enforced 30-second
   boundary. No slot is reserved. Signed discovery responses also expire.
5. Recompute on demand. Source, config, model, profile, authority, enrollment,
   runtime epoch, task or policy changes invalidate the relevant prior state.
   Expired or mismatched proof can remain a declaration, never verification.
6. Use `.revalidate(selection, task)` to rebuild and compare current state. A
   renewed observation with unchanged semantic state does not alone invalidate
   selection; the original selection expiry still limits reuse.
7. Retain the allowlisted `audit` event in the host's existing audit/log facility
   if required. Operator lifecycle transitions remain in existing operator audit
   records. Discovery adds no durable database or background probe loop.

Luna may propose strict requirements and inspect candidates/reasons. A trusted
host must bind them to the real task, current native tool context or enrolled
external supervisors, validated proof readers and admission readers. Luna must
not construct trusted proofs, select credentials, alter policy, approve tasks or
turn a selection into an execution grant. Before any later dispatch, both
discovery revalidation and the existing executor's current authorization remain
mandatory. This module provides no dispatch method or public network endpoint.

### Illustrative use, not live configuration

```python
from agent.discovery import DiscoveryService, SelectionPolicy

# Illustrative validated metadata. The host supplies the real frozen task hash
# and an absolute current deadline; these values come from the fictional fixture.
requirements = {
    "protocol": "cow.discovery.task/1",
    "task_id": "cb4a1ff8-6401-4ce7-8f81-c1fcbd4cf9c6",
    "policy_id": "safe-default",
    "category": "analyze_records",
    "input_contract": "fictional_records.v1",
    "output_contract": "analysis_report.v1",
    "persistent_memory": "required",
    "persistent_context": "required",
    "required_tools": [], "max_authority": ["analyze_records"],
    "approval": "required", "verification": "independent_analysis",
    "recovery": "intent_fenced", "cancellation": "cooperative",
    "deadline": 400.0, "timeout_seconds": 200.0, "concurrency": 1,
    "permitted_mechanisms": ["persistent_named"],
    "prohibited_mechanisms": [], "task_spec_hash": "0" * 64,
    "requested_agent_id": "testpilot",
}
service = DiscoveryService(policy=SelectionPolicy(
    preferred_targets=("testpilot", "testpilot2"),
), clock=lambda: 110.0)  # Synthetic clock only.
# With no native-context or enrolled-external host sources, current registered
# identities (including default) are visible but cannot become eligible.
decision = service.select(requirements)
assert decision["dispatch_permitted"] is False
```

An internal host can supply `NativeSource(existing_delegate_tool, ...)` for a
current `default`-owned turn, and `ExternalSource(existing_bindings_reader)` for
separately enrolled `cowagent.testpilot`, `cowagent.testpilot2` and `codex`
supervisors. The callbacks and their trust obligations are documented in
[`sources.py`](../../agent/discovery/sources.py). Do not manufacture a proof using
the fingerprint supplied to a callback. Load and verify a pre-existing receipt
whose tested fingerprint matches. The reproducible fixtures in
[`test_bullgod_discovery.py`](../../tests/test_bullgod_discovery.py) show synthetic
wiring with temporary journals and fictional records. Their models, times,
credentials and capabilities do not describe current live agents.

## Controlled acceptance

| Scenario | Reproducible assertion |
| --- | --- |
| A: persistent context | Isolated worker excluded; properly enrolled named target qualifies |
| B: stateless | Persistent modes excluded; restricted native worker may qualify |
| C: external development | Codex coding request denied; existing analysis contract does not imply coding |
| D: revocation | Revocation/re-enrollment rejects retained selections and fences task approvals |
| E: model switching | Separate configured models reported; changed model/profile/config invalidates evidence |
| F: unsupported specialty | Natural-language instructions and descriptions never create verified capability |
| G: concurrency | Separate TestPilot runtime boundaries and one slot each; provider parallelism unknown |
| H: no candidate | Structured denial with reasons and no execution |
| I: contradictory context | Required memory plus prohibited context rejected deterministically |

Additional adversarial cases cover HMAC tampering, exact spec/caller binding,
identity substitution, denied persistent fallback, stale health/proof, unknown
load, preference order, input permutations, privacy-safe output, policy/task
changes and absence of transport calls, Agent construction or new intents.
Existing adapter tests are retained unchanged.

## Evidence and limits

- [Preflight](preflight.json): exact baseline/upstream, clean tracked state,
  recovery/untracked preservation and current pCloud Backup/Sync scope.
- [Focused validation](focused-validation.json): 224 passed, including 26 core
  and 26 acceptance cases plus existing adapter/native/operator compatibility;
  Ruff F, compilation and whitespace checks passed.
- [Independent review](review.md): PASS after correcting two P2 findings.
- [Preservation](preservation.json): original service process and runtime metadata,
  config/profile/provider hashes, memory/database stat metadata, untracked files,
  recovery refs/artifacts and existing detached worktree are preserved.
- [Hosted run 42546970682](https://github.com/hottweelz/CowAgent/actions/runs/42546970682):
  all five jobs passed on the source commit above. macOS/Python 3.13, Linux/Python
  3.11 and 3.13, JavaScript, strict TypeScript/build and changed-file Ruff are
  covered. [Receipt](hosted-validation.json): macOS **5,969 passed / 39 skipped**;
  each Linux version **5,962 passed / 46 skipped**; 93 passing subtests per job.
  Each job has 6,008 named cases, including all 52 new discovery cases. No baseline
  case was removed and the exact skip sets are unchanged. JavaScript passed
  39 web and 5 desktop cases. Zero Python failures or errors.
- The hosted synthetic merge tree equals the feature-head tree. The final
  documentation/receipt closeout uses `[skip ci]` and preserves every other
  tracked path, including the seven reviewed source/test hashes. See
  [source equivalence](source-equivalence.json). The closeout does not claim a
  separate CI run. Windows and opt-in native browser exclusions remain outside
  this ordinary macOS/Linux gate; existing build warnings remain recorded.

Synthetic acceptance proves the contract and integration with real temporary
registry/operator/journal APIs. It certifies no current live target capability.
No live or paid model task is required or performed. Missing host proof/admission
readers remain a deliberate fail-closed integration prerequisite. Existing source
fingerprints include this new code; historical live enrollment evidence must not
be reused as fresh approval for changed source.

Unsupported features: autonomous execution, scheduler, public endpoint/dashboard,
new credential registry, memory engine, arbitrary coding or tool execution through
the existing external adapters, continuous probes, cost/quality prediction, slot
reservation, provider-parallelism guarantees, hard termination and exactly-once
effects. No production activation, service restart, profile/memory/provider
change was part of the development milestone. The subsequent authorized merge is
recorded in the integration report.

## Completion questions

| Question | Answer within this milestone |
| --- | --- |
| Discover existing identities without duplicates? | Yes. Derived native registry and explicitly supplied enrolled-supervisor views; no second roster. |
| Separate verified capability from unsupported declarations? | Yes. Current bound proof is required; unknown or stale proof is ineligible. |
| Distinguish the three mechanisms? | Yes. Isolated, persistent named and external runtime contracts remain separate. |
| Exclude unauthorized, unavailable or incompatible targets? | Yes. Deterministic gates cover authority, approvals, health, context and contract compatibility. |
| Select deterministically and explain? | Yes. Versioned preferences, known load and stable tie-breaks; public reasons and fingerprints. |
| Invalidate on authority/configuration changes? | Yes. Revalidation reconstructs current state, including revisions, proof/task/policy bindings and expiry. |
| Allow future Luna integration without bypass? | Yes. Luna can supply requirements and consume results; trusted evidence and existing execution admission remain host-controlled. |
| Preserve execution and memory behavior? | Yes. Discovery has no execution route or memory initialization. Existing execution methods are unchanged; the only existing-source addition is a read-only approval preview. |
