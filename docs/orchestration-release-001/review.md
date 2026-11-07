# Integrated engineering review

One independent Sol 6.1/high reviewer inspected the integrated authority,
durable task, restart, and result-verification paths. Stronger reasoning was
selected because the task joins authorization decisions with persistent attempt
ownership and evidence. The reviewer was read-only; the lead owns fixes,
integration, test acceptance, and Git publication. No HomeBoss or external
worker pool was used.

## Findings reproduced

### P1: guest execution identity became conversation ownership

`AgentBridge` sets `_current_agent_id` to the transcript owner and
`model.agent_id` to the actual speaker. `_prepare_task` used the transcript
owner for the frozen execution identity. A guest's initial child shared the
guest model, but restart restored the host profile and model.

The reviewer reproduced this with actual `_prepare_task` and `restore_child`
and synthetic profiles: initial model `guest-selected`, frozen source and target
`host`, frozen/restored model `host-selected`, restored execution identity `host`.
No model request or network call was needed.

Required correction: keep the task's conversation owner distinct from its
execution principal. Preserve the guest profile/model, while validating the
current host-owned conversation roster, project and permission grants. A
revoked or disabled speaker must not recover with another principal's authority.

### P2: a cancelled waiter could stop a replacement attempt

The non-owner polling path in `execute_task` called task-scoped `request_stop`
then continued polling. An explicit retry between polls could create another
attempt; the old cancelled waiter then stopped that attempt too.

The reviewer reproduced the race using the actual TaskStore, interleaving old
claim release, explicit retry and a new claim immediately after the first stop.
Both old and new attempts were cancelled by the same stale waiter.

Required correction: fence stops to the observed execution generation and
return after recording the stop. A stale waiter must not claim or cancel a
replacement generation, including queued transitions. Trusted operator CLI
cancellation remains a deliberate task-scoped action.

## Other review evidence

- The prior VERIFICATION-001 early-return receipt defect is closed at the
  common stream result boundary. Failed native argument checks and permission
  refusals feed attempt-scoped blocking receipts.
- The reviewer ran **88 focused tests**, all passing, with private HOME/data
  and denied network access. This includes isolation authorization/filesystem/
  delegation, recovery runtime/controls, verification checks/store/integration,
  and delegation timeout/parent cancellation. These tests overlap the final
  regression selection and are not added to its unique count.
- An initial stdin-based test wrapper was unsuitable for macOS multiprocessing
  spawn. That aborted run is excluded; only its owned processes were stopped.
- The reviewer inspected the new crash-boundary and persistence tests and found
  no test-design blocker. Final integrated execution belongs to the lead.
- The nine ChannelsPage errors remain a separate failed required gate. The
  reviewer did not change frontend code or reinterpret that gate as passing.

## Corrections and narrow confirmation

The bridge now records the execution principal separately. The task envelope
retains host journal ownership and guest execution identity. Recovery validates
the enabled owner/speaker and current host roster, project and permission,
while preserving the guest's configured model. Host model pins are not applied
to guests. Pre-fix envelopes already misattributed to a host are not rewritten.

Explicit retry now increments a durable generation. Waiter claims/stops compare
that generation and the observed attempt. A successful stop returns the exact
stopped row from its transaction; a failed stop CAS re-observes completion or
replacement instead of falsely reporting cancellation. Operator task-scoped
stops remain available. The additive migration preserves existing rows.

The lead requested a narrow check of these two corrections, not another broad
review. The same independent reviewer found both reproductions closed and ran
**7 correction tests**, all passing, with private HOME/data and denied network.
These cases are included in the final integrated selection. The lead's final
run passed **1,364 tests**, with **15 skips**; the seven skipped browser cases
passed separately. All 54 changed/new Python files passed F-class Ruff and
compilation. See [regression.json](regression.json).

No live production/provider or hard OS sandbox validation is claimed. The
strict renderer baseline remains the only failed required release gate.
