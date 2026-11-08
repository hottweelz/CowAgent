# EXTERNAL-003B bounded engineering review

Decision: **No remaining blocking source finding for approved bounded analysis.**
This does not authorize a master merge or production activation.

One Sol 6.1/high architect/reviewer assessed the approval/send boundary and the
final implementation. Cross-process authority, WAL transaction atomicity and
uncertain native sends required stronger reasoning than routine Luna work.
The parent owns implementation, validation and release. Requested models were
accepted; their effective delegated identities are not independently exposed.

Reviewed source: ApprovalJournal, operator decision fencing, supervisor submission
and cancellation, Codex runtime admission/publication hooks, and focused gate and
adapter tests. The lead also reviewed the integration and actual acceptance
runner. No additional reviewer chain was used.

The review required one database for operator decisions and external intent,
fresh atomic native admission after configuration attestation, one-shot intent
consumption, delayed-cancellation publication fencing and rejection of legacy
analysis paths. Those boundaries are implemented.

## Finding and correction

Runtime polling initially interrupted without consuming the supervisor's pending
cancellation claim. After a lost reply, automatic reconciliation could then send
a second interrupt without an explicit retry.

The runtime now always sets its local fence, but sends an interrupt only with an
active client, known native IDs and a successful shared durable claim. Supervisor
reconciliation and runtime polling cannot independently consume it. Explicit
cancel retains its deliberate retry behavior.

The reviewer independently ran
`test_operator_cancel_interrupt_loss_needs_explicit_supervisor_retry`: one pass.
It exercises private IPC, a lost first interrupt, repeated polling/reconciliation,
and an explicit retry that confirms scoped cancellation. The full protected
regression subsequently passed on the same product source.

The lead also normalized unknown host-task submission to unauthorized rejection,
enabled foreign keys for the shared operator journal and added a legacy-journal
bypass regression. No hidden approval fallback was introduced.

## Evidence limits

Revocation after native/publication intent cannot retract the committed
authorization. Physical publication may follow its earlier intent. After adapter
restart no live native client exists for interruption; retained state or a cancel
request alone cannot prove termination. The review did not execute native Codex.
The parent's separate actual acceptance passed and is documented in
[README.md](README.md) and [native-receipts.json](native-receipts.json), including
the empty-thread history limitation and retained initial harness failure.
