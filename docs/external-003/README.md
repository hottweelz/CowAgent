# EXTERNAL-003: operator control foundation

Status: **STARTED — review-only first slice.**
Base: merged master `edb704336a1dca0d6d8f81f11432c3097916bc58`.
Branch: `feat/external-003-operator-controls`.

EXTERNAL-002B's bounded adapter is now integrated. The next milestone is an
operator enrollment/approval and uncertainty-resolution flow for that bounded
operation. Real external actions remain disabled until their own authority and
independent verification contracts are tested and activation is authorized.

## First slice

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
This slice does not read native
credentials/configuration, invoke a model, write a journal, register a worker,
start a service, approve a task or dispatch one. Existing adapter controls remain
unchanged. Only disposable fixture data is used for verification.

## Verification

[Validation receipt](validation.json): 22 new packet tests and 50 related
contract/analysis/policy/artifact-verifier tests passed, with no skips or failures.
Ruff F and compilation passed for both new files. Tests cover drift, expiry,
unsupported operations and wider grants, modified enrollment packets, input
copying, separate outcomes and preservation of unsupported caller criteria.
The no-I/O fixture rejects file opens, file writes, process starts and sockets
during builder calls. The lead reviewed the source; a delegated Luna worker
implemented the focused tests. Initial test-draft assertion errors and their
correction are recorded in the receipt.

The accepted EXTERNAL-002B full Python, Node, strict renderer and desktop-build
gates remain the merge baseline. This unwired Python module changes no existing
adapter, UI or dispatch source, so those executions were not repeated. No real
model or external-service calls were made. GitHub returned no Actions run or
commit status for merged master `edb70433`; no remote CI pass is claimed.

## Ordered next work

1. Define the authenticated operator identity and durable decision/audit
   contract. Freeze task, runtime/enrollment revision, authority and expiry.
2. Test grant/revocation, stale approval, conflicting callers, restart and replay
   behavior before connecting approval to bounded analysis dispatch.
3. Add explicit uncertainty inspection/resolution without automatic native
   replay or republishing. Keep worker execution, acceptance and external state
   separate in the operator flow.
4. Add key rotation, retention and resource controls; obtain review before any
   live activation. External-service actions require a separate tested contract
   and independent effect observer.

The existing [merge review](../external-002b/merge-review.md) and accepted
EXTERNAL-002B receipts remain the integration baseline. This new branch does not
broaden those guarantees or modify production state.
