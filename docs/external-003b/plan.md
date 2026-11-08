# EXTERNAL-003B: approval-enforced dispatch and revocation

Base: `036d957f`, branch `feat/external-003b-approved-dispatch`.
Only `analyze_records` is in scope. No master merge or live orchestration activation.
Actual Codex acceptance uses disposable tasks and existing native authentication.

## Transaction contract

Operator decisions and gated external intent rows share `operator.db`. Approval
checks and intent commit in one WAL/FULL transaction, with time sampled after
the writer lock. Attached WAL databases do not provide cross-database atomicity.
The synthetic legacy journal remains separate and cannot authorize analysis.

1. Host submit intent binds current task/enrollment revisions, exact scope/spec
   and credential metadata. No intent means no send; an existing intent prevents
   automatic replay even when its outcome is unknown.
2. After actual native configuration attestation, a second transaction checks
   authority and commits one native turn intent. Existing native intent never
   authorizes another turn. The runtime rejects analysis without the gate.
3. Revocation/replacement decisions atomically fence bound work and queue
   cancellation. Pending cancellation is claimed before bounded IPC; uncertain
   delivery needs explicit repeat. The active runtime also observes the durable
   fence. Cancellation intent never means confirmed termination.
4. Publication needs its own current-authority check and one-shot durable intent.
   Recovery never republishes or starts a replacement native turn.

Revocation before native intent prevents native dispatch. If native intent
commits first, the task was authorized at that point; subsequent revocation asks
for cancellation. It cannot prove that execution never started or all descendants
exited. Do not hold a database write transaction across native/runtime calls.

## Ownership and verification

- Lead: lifecycle, adapter hooks, actual native acceptance, documentation and Git.
- Luna: bounded runtime mapping and migration of adapter fixture tests.
- Terra 6.1/high: shared journal, operator/supervisor integration and gate tests;
  interacting transactions and recovery require more than routine implementation.
- One Sol 6.1/high architect/reviewer: atomicity and final implementation review;
  cross-process authority and uncertain effects require stronger reasoning.

Use actual SQLite races to prove both intent/revocation orderings, expiry after
lock wait, duplicate/conflicting submits and durable cancellation. Adapter
fixtures must prove denial without a native turn during setup revocation/expiry,
delayed IPC publication fencing, interruption and legacy bypass rejection.

Actual Codex gate: combine approved analysis, independent artifact checks and
supervisor crash/restart in one execution; use a second live turn for revocation
and cancellation. Unapproved/revoked tasks must cause no native turn. Preserve
task/session identity and count actual public native turns. Record receipts,
current CLI/policy/config binding and all verification limits.

Run applicable external/operator regressions, strict renderer/desktop gates and
static checks. Reuse unchanged accepted evidence where valid; changing adapter
source requires fresh native evidence. Publish README, review and receipts,
update project continuity, commit/push and require upstream 0/0. Preserve all
production state and unrelated untracked files.
