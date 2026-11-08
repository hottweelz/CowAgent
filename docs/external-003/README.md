# EXTERNAL-003: operator control foundation

Status: **STARTED — local operator decisions tested; dispatch remains disabled.**
Base: merged master `edb704336a1dca0d6d8f81f11432c3097916bc58`.
Branch: `feat/external-003-operator-controls`.

EXTERNAL-002B's bounded adapter is now integrated. The next milestone is an
operator enrollment/approval and uncertainty-resolution flow for that bounded
operation. Real external actions remain disabled until their own authority and
independent verification contracts are tested and activation is authorized.

## Review-packet foundation

Implemented pure enrollment and task-review packet builders in
[`operator_review.py`](../../agent/external/operator_review.py), protocol
`cow.external.operator-review/1`. Each packet binds its supplied
configuration/evidence fingerprints, claimed caller identity, normalized task
hash, proposed grant expiry and verification requirements. Broader operations
and grants are rejected. Configuration/probe drift and expired authority produce
blocked drafts. Modified enrollment packets are rejected on task review.
All packets carry execution/external-actions disabled and approval not granted.

`build_enrollment_review(enrollment, current=..., observed_probe_sha256=...)`
compares the seven public enrollment fields with supplied observations. It checks
the supported CLI/policy revision without opening configuration files.
`build_task_review(spec, enrollment_review, now=...)` accepts only
`analyze_records` with exactly that proposed operation grant. Its digest binds
identity, task, dataset, artifact name, enrollment draft and normalized caller
criteria. Unsupported caller checks remain visible; no check is claimed to pass.

These are drafts, not credentials or authenticated decisions. A hash binds
contents but does not establish provenance, operator identity, fresh runtime
state or authenticity of a probe receipt. `review_required` means the supplied
values agree, not that enrollment or execution is approved. Task outcomes remain
separate: execution `unobserved`, acceptance `unverified`, external state
`unverified`. Supplied observations are labeled as caller-provided.
The draft builders do not read native
credentials/configuration, invoke a model, write a journal, register a worker,
start a service, approve a task or dispatch one. Existing adapter controls remain
unchanged. Only disposable fixture data is used for verification.

## Local operator enrollment and approval

The owner selected enrollment and approvals before uncertainty resolution.
[`operator_control.py`](../../agent/external/operator_control.py) now records
explicit local operator decisions. [`operator_cli.py`](../../agent/external/operator_cli.py)
provides `init`, `apply`, `status` and `audit`. It has no dispatch, runtime start,
network listener or external-action command. The [plan](plan.md) defines scope.

The operator is the POSIX account that owns the private state directory and
journal. Real and effective UIDs must agree. No `approved_by` value is accepted
from command data. This is account authentication, not human-presence proof or
distinct identities for people who share an account. Same-account code and root
remain trusted. No native OAuth, model/provider settings or credentials are read.
The kernel identity APIs are defined by [Python's OS interface](https://docs.python.org/3/library/os.html#os.geteuid).

State requires an explicit canonical absolute directory. The leaf and journal
must be owner-only; database/companion symlinks and hard links are rejected.
Ancestors must belong to root or the current account and cannot permit group or
other writes unless sticky-directory protections apply. The journal uses
WAL/FULL. Each decision, revision and audit snapshot commits in one
`BEGIN IMMEDIATE` transaction. Expiry is sampled after acquiring the writer lock;
status reads use one snapshot. This follows [SQLite transaction semantics](https://www.sqlite.org/lang_transaction.html).

```sh
python -m agent.external.operator_cli --state-dir /absolute/private/operator-state init
python -m agent.external.operator_cli --state-dir /absolute/private/operator-state apply --request command.json
python -m agent.external.operator_cli --state-dir /absolute/private/operator-state status --scope scope.json
python -m agent.external.operator_cli --state-dir /absolute/private/operator-state status --scope scope.json --task-id TASK_UUID
python -m agent.external.operator_cli --state-dir /absolute/private/operator-state audit --scope scope.json
```

These commands manage local decisions only. `-` can supply request/scope JSON on
stdin. There is no default production directory. Parent directories must already
exist. Initialize only an explicitly chosen operator-state directory; production
activation is not authorized by this report.

Commands have exactly `protocol: "cow.external.operator-command/1"`, a UUID
`request_id`, `action`, `scope`, nonnegative integer `expected_revision` and
`payload`. Scope has exactly `supervisor_id`, `owner_id`, `source_id`,
`conversation_id` and `runtime_id`; these bind the decision but do not prove a
remote caller identity. Use the review builders above to construct frozen drafts.

| Action | Payload | Result |
| --- | --- | --- |
| `enroll` | `review`, `expires_at` | Approve a matching enrollment draft for this scope |
| `approve_task` | `spec`, `enrollment_revision`, `task_review_id`, `reviewed_at`, `expires_at` | Approve the exact bounded analysis draft under the current enrollment |
| `revoke_enrollment` | `{}` | Invalidate the enrollment and its existing task approvals |
| `revoke_task` | `task_id` | Revoke this task decision |

Revision starts at zero for an absent target and increments for each new
decision. Task approvals cannot outlive task authority or enrollment. Task IDs
cannot be rebound to changed specifications or caller scope. Re-enrollment uses
a new revision, so prior task approvals do not become current again.

Exact request retries return the historical receipt and current state without
reapplying the decision. A reused request ID with different input or a stale
expected revision is rejected. `receipt.historical` is always true;
`current.approval_status` and `current.approval_current` describe present local
decision validity. Revoked or expired approvals stay ineffective after restart.
Audit entries preserve the actor UID, request ID, revision and decision snapshot.
The journal is not tamper-proof against its owning account or root.

**An approved local decision is not execution authority.** Every response keeps
execution and external actions disabled. These records are not passed to
`ExternalSupervisor.approve()` or `submit()`. Revocation here does not cancel an
already-running task. Fresh native attestation, an atomic approval/submit boundary
and explicit activation authorization are still required before dispatch can use
this workflow. No new service effects or automatic uncertain replay are added.

## Verification

[Operator validation](operator-validation.json) records **79 unique passes**:
26 operator-control tests, ten CLI tests and 43 review/contract/supervisor
regressions. The final control-file run includes the corrected lock-wait case;
earlier repetitions are not added to the denominator. The CLI test runs separate actual Python
processes through initialization, enrollment, task approval, revocation, restart
status and original-request replay against disposable SQLite state. These are
real local workflow executions, with fictional data and no native agent calls.

Tests cover conflicting revisions, scope/spec binding, expiry after lock wait,
revocation and re-enrollment, restart, immutable audit snapshots, replay, malformed
numeric input and unsafe state paths. Ruff F and compilation pass for four new
files. The [independent review](operator-review.md) has no remaining blocking
finding for this local-account scope. Other-UID attacks were not executed; path
ownership/mode and changed-UID denial checks are fixture evidence.

The original foundation [validation receipt](validation.json) below is retained
at its `fcfd0377` source, not presented as a new execution of this operator flow.

Foundation receipt: 22 packet tests and 50 related
contract/analysis/policy/artifact-verifier tests passed, with no skips or failures.
Ruff F and compilation passed for both new files. Tests cover drift, expiry,
unsupported operations and wider grants, modified enrollment packets, input
copying, separate outcomes and preservation of unsupported caller criteria.
The no-I/O fixture rejects file opens, file writes, process starts and sockets
during builder calls. The lead reviewed the source; a delegated Luna worker
implemented the focused tests. Initial test-draft assertion errors and their
correction are recorded in the receipt.

The accepted EXTERNAL-002B full Python, Node, strict renderer and desktop-build
gates remain the merge baseline. These local controls change no existing
adapter, UI or dispatch source, so those executions were not repeated. No real
model or external-service calls were made. GitHub returned no Actions run or
commit status for merged master `edb70433`; no remote CI pass is claimed.

## Ordered next work

1. Review the local-account trust boundary before production use. If distinct
   human identities or presence are required, establish and test that contract.
2. Connect current local decisions to bounded analysis only after testing the
   atomic approval/revocation/submit-intent boundary and fresh runtime enrollment
   checks. A current decision or matching supplied fingerprint alone is insufficient.
3. Add explicit uncertainty inspection/resolution without automatic native
   replay or republishing. Keep worker execution, acceptance and external state
   separate in the operator flow.
4. Add key rotation, retention and resource controls; obtain review before any
   live activation. External-service actions require a separate tested contract
   and independent effect observer.

The existing [merge review](../external-002b/merge-review.md) and accepted
EXTERNAL-002B receipts remain the integration baseline. This new branch does not
broaden those guarantees or modify production state.
