# BULLGOD-DISCOVERY-002

**DISCOVERY-002R source implementation is complete; live integration is BLOCKED.**
The [in-process remediation report](in-process-remediation.md) records the trust
decision published before code, the internal initialized-runtime bridge, all A–J
results and ten completion answers. Source `209f4e0f` passed 345 focused tests
(including 20 new cases) and independent source/test review. Both Linux jobs, JavaScript/strict TypeScript/build and Ruff passed; the
[hosted macOS gate](in-process-hosted.json) is BLOCKED after two runner-acquisition
failures, with no macOS test steps executed. The existing PID has no verified supported authenticated way
to load/invoke the new bridge under the no-restart constraint; no PARTIAL or
PASSED live-native result is claimed. [Preservation evidence](in-process-preservation.json)
confirms the unchanged service, profiles and aggregate records. Private authority
still expires normally and ignored-ownership sources still reject. PR #4 stays
draft and unmerged. The original 002 results below remain historical evidence.

Gate A is **PASSED**. DISCOVERY-001 merged normally through
[PR #3](https://github.com/hottweelz/CowAgent/pull/3) as
`40958f392bca59009224fcebfd1b636a861615ab`. Automatic master CI passed all five
jobs. The documentation-only integration closeout is
`f659349785acf98905901a5cc53921436a109dbc`, the verified base of
`codex/bullgod-discovery-002`. See the
[integration report and receipts](../bullgod-discovery-001/integration.md).

Gate B implementation and independent source review are complete, but the
required trusted live selection gate is **BLOCKED**. The actual APFS volume has
ownership enforcement disabled. Its root initially had mode `0775`. After the
maintainer explicitly approved that one change, the root was changed to `0755`;
owner enforcement was not enabled. A fresh read-only check still returned
`filesystem_ownership_ignored` before registry loading, binding or selection.
See the [authorized change](authorized-volume-mode-change.json) and
[post-change rejection](after-authorized-mode-change.json).

The initial mode-only proposal was withdrawn after the ownership issue was
found. The later explicit approval authorized only the mode change, not ownership
enablement or any broader storage change. No config/profile content, credential,
approval or model setting changed. All 356 focused tests, the independent review
and all five final hosted jobs pass on source
`10dac8d33f52204f80ee61c6ae19373851e77f82`.

A [read-only ownership impact assessment and proposed operation](ownership-remediation-plan.md)
is now available. It confirms volume-wide scope, administrator requirements,
shared active application dependencies and rollback limits. Ownership enablement
has not been authorized or executed.

The separately readable private enrollment records are expired. These observations
cannot supply missing native configuration or proof provenance. No production
activation is part of this work.

Implementation and evidence are published in [draft PR #4](https://github.com/hottweelz/CowAgent/pull/4). DISCOVERY-002 is not merged.

## Architecture and authoritative sources

The [plan and trust decision](plan.md) preserve the existing registry, operator
journal, adapters, permission evaluation and selection engine. There is no second
identity registry, scheduler, memory store, authority service or public endpoint.

| Reader | Authoritative input | What it establishes |
| --- | --- | --- |
| `ReadOnlyNativeConfiguration` | Existing config and strict team roster | Registered identity, enabled state, profile and configured model/provider declarations |
| Attached native source | Existing current `AgentDelegateTool` and initialized recovery service | Current caller/team/policy/authority constraints; available initialized liveness or busy evidence |
| `ExistingRuntimeBinding` | Existing private credential/launch file, exact frozen spec and initialized operator journal | Runtime and caller scope; no guessed identity or new credential |
| Read-only operator view | Existing private account-owned journal, schema, state and matching audit snapshot | Current enrollment/task decision, revision, expiry, revocation and exact task binding |
| Probe reader | Existing approved probe bytes and supported receipt schema | Provenance under operator-account trust and complete tested-source applicability |
| Explicit authenticated inspection | Existing running adapter, real HMAC action/nonce and frozen enrollment | Fresh runtime observation, current supported attestation and measured admission facts |

The Codex runtime in the retained records is **`acceptance-runtime`**. Its adapter
is Codex, but its identity is not renamed to `codex`. Named runtime IDs remain
`cowagent.testpilot` and `cowagent.testpilot2` and must match native registration.

The file-only native reader does not call `load_config`, construct an Agent,
initialize memory or replace the running service's configuration. File settings
are declarations, not proof of current service environment or in-memory state.
A trusted in-process host can supply a verified effective-settings source. The attempted offline
acceptance stopped at path validation. Separate public service metadata confirms
the observed IDs and route declarations, but is not substituted for a trusted
registry or live in-memory attestation.

## Proof lifecycle and trust boundary

Operator records are authenticated through the existing private local account,
trusted ancestors, ownership/mode/schema checks and state/audit consistency.
On Darwin, `statfs64`/`fstatfs64` must also show ownership enforcement. The
`MNT_IGNORE_OWNERSHIP` flag is not present in Python `statvfs` output. The reader
fails closed if the authoritative API is missing or fails. Linux retains the
existing checks. [Mount evidence](mount-ownership.json) confirms the actual
workspace is rejected and private temporary storage is accepted. No host
ownership-enforcement or mount setting was changed. The later approved root-mode
change is recorded separately. Operator provenance is not a signed or tamper-proof
audit log, proof of human presence or protection
from same-UID/root code. Review packets and content hashes alone do not establish
provenance. Luna has no path or proof field in task requirements with which to
replace these trusted host inputs.

The probe reader checks the exact approved digest, supported receipt shape,
passing assertions and relevant contract/source/model/configuration bindings.
For named capability, the receipt must bind the complete tested native source
fingerprint to the approved and current source. Historical focused receipts with
only partial source maps remain insufficient even when their bytes were approved.
Fresh re-enrollment cannot extend old proof to code it did not test.

Fresh inspection is independently authenticated. The actual `inspect` action and
request nonce remain bound to the HMAC response; the host never re-signs cached
data as a fictional discovery response. Inspection carries the opaque fingerprint
of the running adapter's **entire** frozen enrollment, including `probe_sha256`.
It must match the full currently approved enrollment before proof can qualify.

Current source, config, profile, model/provider, exact input/output and verification
contracts, credentials, task/enrollment state and fresh observation must all agree.
Changes or revocation invalidate proof and retained selections. Missing evidence
remains missing. No record is enrolled, approved, submitted or refreshed by a
reader.

## Admission semantics

Public `runtime_state` distinguishes registered/enabled, enrollment status,
authorization, exact task approval, credential validity, health, availability,
capacity, revocation, expiry and unknown state. `proof_status`, provenance,
fingerprints, expiration and sanitized reason codes explain failures.

An existing process or socket is not an admission grant. Inspection is an explicit
host operation with `contact_authorized=True`; selection and revalidation make
zero IPC contacts. Successful and failed-contact observations have bounded
lifetimes of at most 30 seconds. Expired unavailable observations become stale or
unknown. A current task still needs its exact operator approval at execution.

Named inspection reads existing adapter state under its mutex, checks the full
frozen enrollment and pure current native snapshot, and observes its serial
admission boundary. It does not invoke native preparation, model execution,
memory initialization or the old discovery operation. No capacity is reserved.

The native isolated path requires a real attached caller turn for team, cycle,
depth and authority facts. An offline roster cannot provide those facts. Existing
initialized recovery liveness and busy evidence can be observed without creating
a task store, claiming work or locks. No coherent global free-slot or current
native capability-proof source exists, so these values remain unknown.

Codex inspection does not run `codex --version`, start app-server, call policy
discovery or create a workspace. A responding adapter can establish that response's
health, but current installed-executable/native attestation and free capacity
remain unknown where existing infrastructure cannot safely prove them. The
analysis capability is not promoted to general coding authority.

## Supported internal interface

The implementation is in
[`runtime_readers.py`](../../agent/discovery/runtime_readers.py). Host-only setup
can use existing in-memory supervisors or:

```python
binding = ExistingRuntimeBinding.from_private_files(
    operator_dir=existing_operator_directory,
    credential_path=existing_private_credential_or_launch_file,
    spec_path=existing_frozen_task_file,
    probe_receipt_path=existing_approved_probe,
    config_path=existing_native_config,
    socket_path=existing_socket,  # Optional; launch files can supply it.
)
host = TrustedDiscoveryHost(
    native_configuration=ReadOnlyNativeConfiguration(existing_native_config),
    external_bindings_source=lambda: (binding,),
)
# Only an explicitly authorized observation may contact an existing adapter.
observations = host.observe_external(
    [binding.supervisor.transport.credential.runtime_id],
    contact_authorized=True,
)
decision = host.select(trusted_requirements)
check = host.revalidate(decision, trusted_requirements)
assert decision["dispatch_permitted"] is False
assert check["dispatch_permitted"] is False
```

These are host objects and private operational inputs, not task/model arguments.
The factory accepts the existing named launch format and the legacy Codex
secret/expiry format. For the latter it recovers the original identity from the
existing exact task and approval binding; it does not invent a key ID or runtime.
Read-only journal opening checks existing schema and never creates tables.

Luna may propose strict requirements and inspect the sanitized decision. The host
owns binding selection, current trusted evidence, policy and contact authorization.
Later dispatch must independently pass the existing current admission and
authorization gates. There is no dispatch method or execution grant in this API.

## Actual runtime acceptance

**Trusted integrated run: BLOCKED at `read_actual_config`.** No live selection
scenario ran. The runner preserved its sanitized failure receipt. Initially,
group-write permission was also present on an ancestor of config
and public proof sources; the approved change removed it. Ownership remains
disabled, so the native mount guard still rejects both sources. The
[first ownership rejection](live-ownership-rejection.json) and
[post-permission-change rejection](after-authorized-mode-change.json) both stop
safely on repaired source with all runtime/configuration metadata unchanged. The guard
must not be bypassed with a copied config, unchecked registry callback or API
metadata. A separate read-only private authority inventory and before/after
service records are available in the [authority receipt](retained-authority.json)
and [preservation receipt](runtime-preservation.json). The
[blocked-run receipt](live-acceptance-blocked.json) records the exact stop stage.

The following table defines required scenario coverage; it does not assert that
the blocked live run completed it.


The original CowAgent service remains the target. Registry identities are
`default`, `testpilot` and `testpilot2`. Actual external records come from the
retained named/Codex authority stores, not synthetic replacement enrollments.
The exact historical probe receipts remain unchanged:

- Named: `docs/agent-routing-003/merge-final-regression.json`.
- Codex: `docs/external-002b/authority-probes.json`.

| Scenario | Actual result |
| --- | --- |
| 1: actual registry | Public service metadata reports all three expected IDs; trusted file registry loading blocked |
| 2: named analysis | Real private enrollments, tasks and credentials all expired; integrated capability selection not reached |
| 3: isolated stateless | Deterministic fixtures pass; actual attached caller context and trusted native policy evaluation unavailable |
| 4: external Codex | Real private identity is `acceptance-runtime`, operation `analyze_records`; unsupported coding rejection passes in fixtures |
| 5: stale/missing proof | Strict path rejection prevents proof use; proof lifecycle and stale evidence denial pass in fixtures |
| 6: approval state | Actual enrollment and exact-task state are separately observed as expired; valid/missing/revoked cases pass in disposable stores |
| 7: unavailable | Synthetic observation against actual metadata not reached; unavailable and expiration fixtures pass |
| 8: drift/revocation | Disposable authority/evidence tests pass; actual approvals untouched |
| 9: revalidation | Disposable selected-then-drift tests pass; no positive actual selection claimed |
| 10: zero dispatch | Failed-run window and independent authority read preserve records/counts; full integrated live instrumentation not reached |

The real private authority receipt reports one prior submit/native/publication
intent for each named runtime and five/three/one for Codex, unchanged after the
read. All three retained task IDs already started submission historically and
must not be replayed. Credentials, enrollment and task approval are expired.

The original process remains PID `28093` with the same start time and health.
Config/profile hashes and public model declarations match before/after.
The observed default route is `nvidia/nemotron-3.5-super-vl:free` via `custom`;
this public declaration is not current authenticated model admission proof.
Aggregate sessions/messages/runs remain `4/7/6` for default, `8/30/11` for
TestPilot and `1/2/1` for TestPilot2. Database inode, size and modification time
are unchanged. The provider environment file's presence was checked; private
contents and usage extras were not read by the metadata snapshots.

Aggregate conversation checks use a read-only SQLite connection with an authorizer
that permits only `COUNT(agent_id)` grouped by `agent_id` on sessions, messages and
runs. It rejects content columns and writes. No title, message, prompt, transcript,
chunk or usage-extras data is read. System observation/log bookkeeping is kept
separate from task, native, model, publication and conversation effects.

The acceptance script is retained as a reproducible check. Its later selection
and synthetic-unavailable sections were **not reached**. No positive live
selection, current proof qualification or selected-then-revoked live result is
claimed. Independent disposable tests establish those code paths only.

## Review, validation and limits

One independent high-reasoning review identified four concrete issues, all now
corrected: disabled-candidate isolation, expiration of negative observations,
running full-enrollment binding, and complete tested-source proof binding.
The corrective review reported **PASS**, with no remaining actionable finding.
The [focused receipt](focused-validation.json) records **356 passed**, including
54 new reader/acceptance cases. [Review findings](review.md) distinguish source
review from the blocked live gate. Final [hosted run 42558258829](https://github.com/hottweelz/CowAgent/actions/runs/42558258829)
passed all five jobs on source `10dac8d33f52204f80ee61c6ae19373851e77f82`.
The [hosted receipt](hosted-validation.json) binds logs, JUnit artifacts and the
synthetic merge checkout to that source.

| Final hosted job | Result |
| --- | --- |
| macOS, Python 3.13 | 6,023 passed; 39 skipped |
| Linux, Python 3.11 | 6,016 passed; 46 skipped |
| Linux, Python 3.13 | 6,016 passed; 46 skipped |
| JavaScript / TypeScript / build | Passed |
| Ruff | Passed |

Each Python job has 6,062 named cases and 93 passing subtests. All 54 new cases
pass; no existing cases were removed and skip identities match Gate A exactly.
The [first hosted receipt](hosted-before-ownership-fix.json) remains attached to
its earlier source. Documentation-only closeout does not change tested code.
[Publication/source equivalence](publication.json) and [preservation](preservation.json)
record the final boundary.

The supported operation remains `analyze_records`. No general coding, arbitrary
file/network effects, autonomous selection-driven execution, background probe
service, new public API, credential minting, approval refresh, hard termination,
exactly-once guarantee or provider-parallelism claim is added.

Before Luna can request an authorized dispatch, the maintainer must first
establish trusted config and proof-source ancestry through an explicitly approved
storage/ownership change, or authorize a separately reviewed trusted in-process
integration. Rerun read-only live selection after that trust issue is resolved.
This milestone does not authorize either host change.

An operator must then separately
provide valid current enrollment/proof, exact task approval and an existing
authenticated runtime with a current supported admission observation. The host
must bind the task and policy and revalidate immediately before the existing
executor's own admission. Missing native/Codex attestation or capacity cannot be
filled by Luna's assertions or historical model output.

## Completion questions

1. **DISCOVERY-001 integration:** Yes. PR #3 merged at `40958f39`; the automatic
   master matrix passed and master was synchronized at documentation closeout
   `f6593497`.
2. **Actual identity enumeration:** Public service observations report `default`,
   `testpilot` and `testpilot2`. Separate private records identify the two named
   runtimes and `acceptance-runtime`. Integrated trusted enumeration is blocked
   by config ancestry; these observations do not replace that gate.
3. **Trusted verified capability:** Implemented and proven with disposable
   authority/IPC cases. No current real capability is certified: source/proof
   ancestry, expired authority and absent fresh attestation remain barriers.
4. **Available versus registered:** The implementation keeps these states
   separate. Real sockets and past success are not admission evidence; actual
   live admission remains unknown.
5. **Current task approval:** Existing private journal state can report exact
   task and enrollment approval separately. Expired approval cannot authorize a
   task; no fresh approval was manufactured.
6. **Fail closed:** Yes. Adverse fixtures pass and the actual unsafe ancestry
   stopped live acceptance before selection.
7. **Revalidation:** Disposable selected-then-drift/revocation cases pass. No
   positive real selection existed to revalidate in this run.
8. **Zero dispatch:** Independent fixture instrumentation checks selection and
   authenticated inspection. The blocked real attempt did not reach selection;
   its before/after records and limits are reported separately. It must not be
   described as successful full live no-dispatch acceptance.
9. **Service preservation:** Before/after metadata checks cover the original
   process, health, profile/config hashes and aggregate conversation counts.
   Private memory contents are excluded.
10. **Before Luna dispatch:** Resolve the config/proof trust boundary through a
    separately authorized change, pass real read-only selection, establish
    current complete proof/enrollment, exact task approval and authenticated
    runtime admission, then revalidate through the existing executor. A discovery
    decision always retains `dispatch_permitted=false`.
