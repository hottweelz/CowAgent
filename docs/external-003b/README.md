# EXTERNAL-003B: approval-enforced dispatch and revocation

**Decision: READY FOR REVIEW for explicitly enrolled `analyze_records` tasks.**
Actual Codex execution, revocation, crash recovery and independent artifact
verification passed. This branch does not activate production orchestration or
authorize a master merge. No email, publishing, payment, browser or other service
operation was added.

Base: EXTERNAL-003 `036d957f`; branch `feat/external-003b-approved-dispatch`.
The [plan](plan.md), [review](review.md), [native receipts](native-receipts.json)
and [regression receipt](regression.json) describe the verified scope.

## Atomic authorization

[`ApprovalJournal`](../../agent/external/approved_dispatch.py) stores external
task records beside operator decisions in the same private `operator.db`.
Every admission samples expiry after `BEGIN IMMEDIATE` acquires the writer lock,
checks current scope/spec/approval/enrollment bindings and commits its intent in
that transaction. There is no separate check followed by an unprotected intent
write. Cross-file WAL transactions are not assumed atomic; SQLite explicitly
limits that guarantee. [SQLite ATTACH semantics](https://www.sqlite.org/lang_attach.html)

| Boundary | Required check | Durable result |
| --- | --- | --- |
| Supervisor send | Current task and enrollment approvals, exact identity/spec, expiry and credential metadata | Bound approval receipt and `submission_started`/`submit_intent` commit together |
| Native turn | The same current approval, exact native enrollment and fresh Codex configuration attestation | One-shot `native_intent` binds native thread/session before `turn/start` |
| Artifact publication | Current authority, no durable cancellation and an existing native intent | One-shot `publication_intent` before atomic artifact replacement |
| Revocation or replacement decision | Expected operator revision and scope | Decision/audit and cancellation fences for bound tasks commit together |

Intent commit is the ordering boundary. Revocation committed **before native
intent** prevents that native turn. Revocation committed afterward requests
cancellation; it cannot establish that execution never started. The same rule
applies to publication: revocation after publication-intent commit cannot retract
an already authorized artifact replacement, even if the physical write follows
the revocation. No database write transaction spans a native RPC or model run.

The runtime's own journal remains separate. If the process dies between the
operator native-intent commit and its local intent write, the operator intent
still prevents another turn. Neither an existing host intent nor native intent
can authorize replay. Uncertainty is retained for inspection.

## Runtime enforcement and cancellation

The generic supervisor rejects analysis without `ApprovalJournal`; a free-form
`approved_by` label is insufficient. `CodexRuntime` rejects new submissions
without its required approval gate and validates the stored receipt before
queueing. It checks again after actual native configuration attestation. The
adapter reports `cow.codex/2` and advertises analysis as approval-required.

Revocation durably marks affected tasks for cancellation before any IPC. An
explicit supervisor flush or reconciliation claims pending delivery before
sending it. The active native worker also observes the shared fence. These paths
share one claim, so losing an interrupt does not allow the other path to resend
it automatically. Explicit `supervisor.cancel(task_id)` can retry. Local
publication remains fenced even if cancellation delivery is lost.

Cancellation requested, native interruption observed and all descendants exited
are different facts. Native terminal observation plus the enrolled effect
boundary supports only `termination_scope: task_effects`. All-descendant exit and
hard cost ceilings remain unproven. After an adapter process restart there is no
live native client in its client registry; persisted cancellation does not prove
that a native interrupt was sent. Recovery reads existing history and never
starts or republishes work. The public native protocol remains app-server stdio;
no internal RPC or exposed supervisor endpoint was added.
[Official Codex app-server protocol](https://learn.chatgpt.com/docs/app-server)

## Actual Codex evidence

Tested CLI: **0.165.0**, macOS; existing native model/provider selection and OAuth
remain runtime-owned. Full configuration hashes matched the retained authority
enrollment before and after both acceptance attempts. The native permission
profile is unchanged from EXTERNAL-002B.

| Case | Observed result |
| --- | --- |
| Unapproved, revoked, legacy-label and unsupported-effect requests | Rejected; no runtime task row or host send intent for the denied analysis |
| Approved analysis with supervisor SIGKILL after runtime acceptance, before host observation | Same task/session recovered; one original native turn; no duplicate send |
| Independent artifact verification | Seven-record result: paid 15,500, refund -2,500, pending 8,000, net 13,000 cents; four accepted records and three exceptions; acceptance and observed artifact verification passed |
| Revocation during actual configuration attestation | No native intent; runtime reports approval unavailable; outbound RPC instrumentation records no `turn/start` |
| Revocation after actual model activity | Durable cancellation initially unconfirmed; later scoped cancellation observed; no artifact published |
| Adapter SIGKILL after native intent, before the outbound `turn/start` | Same native/task identity and durable intent after restart; no outbound turn attempt or artifact; state stays running/unknown, not falsely terminated |

Two model turns were executed across the acceptance attempts. The first attempt
passed the denial and success/crash/verification cases, then its empty-thread
history query failed with RPC `-32600`, `thread not loaded`. A fresh public
observer could not load that thread's history. The harness now records history
as unavailable and separately captures fsynced outbound RPC attempt metadata.
An unavailable history is **not** counted as an empty native history.

Only uncovered cases were continued with new disposable task IDs after checking
unchanged product hashes, configuration, enrollment and credential expiry. The
successful task was not rerun. Original partial-attempt receipts are retained.
Accepted empty-thread cases combine direct host RPC evidence with durable gate
state; this does not assert knowledge of otherwise unavailable native history.

```sh
.venv/bin/python docs/external-003b/run_native_acceptance.py --execute --executable /absolute/path/to/codex
```

This command creates fresh private fixtures and native test history and uses
existing native authentication. It requires explicit execution. Its narrowly
scoped `--resume` option continues a retained acceptance fixture only after source
and configuration checks; it does not resume an uncertain task or renew grants.
No production CowAgent memory, configuration, history or task journal was changed.
Published receipts exclude IPC secrets, OAuth material, raw prompts and logs.

## Regression and review

- Full protected Python suite: **1,527 passed, 15 skipped**, 1,542 unique IDs
  across 131 files, zero failures/errors. Seven exact native-browser cases reused
  with matching source hashes give **1,534 unique passes and eight Windows-only
  skips**.
- Fresh Node UI: **39 passed**. Strict renderer typecheck: **zero diagnostics**.
  Desktop build passed with retained font-path, Browserslist, import/chunk
  warnings. The historical ChannelsPage type errors were not suppressed.
- Ruff F and in-memory compilation passed for eight changed/new files. Product
  and test hashes match the accepted executions. Fixture tests cover conflicting
  decisions, expiry after actual SQLite lock wait, both revocation/intent orders,
  queued revocation, delayed response/cancellation and publication fencing.
- One independent Sol 6.1 review found an overlapping cancellation-delivery
  claim. The fix and lost-interrupt regression were independently confirmed; no
  blocking source finding remains for this bounded contract.

The full suite logged `SQLITE_IOERR_FSTAT` (1802) at `PRAGMA journal_mode=WAL` for
an ephemeral test index. This differs from the suite's deliberate injected I/O
errors. It caused no failing test, but its root cause is unconfirmed. The
diagnostic is retained in the regression receipt as an unresolved test-environment
issue; a passing suite is not presented as a clean log. Memory implementation was
not changed by this milestone.

## Deployment limits and next step

This is an explicit trusted-host integration, not automatic application startup
or a new worker tool. Existing standalone operator approvals do not themselves
launch anything. Old analysis submissions that lack the shared gate now fail
closed; there is no automatic migration of old journals or production activation.
The synthetic legacy test operations do not gain native Codex authority.

The local OS account, root and system clock remain trusted. This is not proof of
human presence, malicious same-account isolation or tamper-proof audit. Broader
operations require their own authority and independent effect-verification
contracts. Review this branch before merge or activation. Explicit uncertainty
resolution, operational key/retention controls and the separate temporary-index
diagnostic remain follow-up work.
