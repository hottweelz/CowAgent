# Independent security and architecture review

One Sol 6.1/high reviewer inspected the external contract, transport, supervisor,
journal, synthetic process, verifier and relevant native broker/recovery seams.
This assignment needed cross-boundary reasoning about authenticated identity,
approval authority and durable effect uncertainty. It was read-only; no HomeBoss
or external worker pool was used. The runtime accepted the requested model;
effective model identity is not independently exposed.

## Finding and correction

**P2: querying a prepared task could permanently prevent submission.**
The initial implementation inferred whether dispatch had started from transport
availability. A status query on an unsent task changed `not_sent` to `unreachable`;
the next submit refused dispatch. The reviewer reproduced zero submit calls
after prepare, status, submit with a private journal.

The correction stores `submission_started` separately and sets it in the same
transaction as `submit_intent`. Status/result for an unsent record performs no
transport call. Unsent cancellation prevents dispatch. A started submission
remains non-replayable regardless of later transport status.

The original reviewer checked only this correction and ran
`test_prepare_queries_do_not_poison_submission_and_unsent_cancel_prevents_it`
through the actual fixture socket: **one passed; P2 closed**. The full regression
contains the same case, counted once. No broader second review was performed.

## Architecture assessment and limits

No other blocking issue was found for the controlled synthetic milestone:
request/identity binding, frozen task inputs, session/revision fences, private
Unix IPC, independent runtime ownership, intent-before-effect and status-only
reconciliation align with the design. External records do not enter the native
recovery dispatch queue; restricted worker capabilities remain unchanged.

- `approved_by` is trusted-host attribution, not an independently authenticated
  human identity. A real approval service is future integration work.
- The synthetic ledger observer confirms only the fictional SQLite effect.
- Lost cancellation is retained but not automatically redelivered. An operator
  must explicitly repeat cancellation after contact returns.
- Artifact checks prove their declared artifact state. They do not prove a
  different external effect; `record_effect` needs a `synthetic_effect` criterion
  when that ledger effect is the desired independently confirmed state.

The reviewer ran the finding reproduction and correction case, not the full
release suite. Parent-owned regression and receipts are linked from README.md.
No production data, real credentials, external agent or live provider was used.
