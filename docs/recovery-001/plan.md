# RECOVERY-001 implementation plan

Baseline: published isolation branch `5b0bb0be`. Dedicated branch:
`feat/recovery-001-durable-tasks`. No production database changes, deployment or
master merge. Keep SQLite/WAL, indexing, request accounting and worker authority.

User-selected policy: automatically recover safe interrupted tasks; require an
explicit operator retry when an effect might already have happened.

## Contract

1. Persist an immutable task envelope before dispatch. Separate task identity,
   attempts, execution owner, stop reason, result and tool-effect receipts.
2. Use a separate protected SQLite WAL journal under shared memory/recovery.
   Storage failure stops task dispatch. Existing history/index files are untouched.
3. Hold a POSIX task lock through the whole attempt. Reconciliation never steals
   a live task by timer. SQL attempt checks fence stale completion and tool calls.
4. Persist tool intent before executing a mutable operation, and persist outcome
   after it. Any interrupted attempt with a mutable intent requires operator
   review/retry, even if the operation may have finished successfully. Do not
   replay completed tasks. This is conservative effect handling, not exactly-once
   external execution or partial model-token continuation.
5. Reconstruct safe interrupted tasks as new attempts from their frozen task
   input. Revalidate identity, current settings, model and caller/receiver grants;
   permissions can narrow but cannot expand. Never initialize private peer history.
6. Preserve cancellation versus timeout durably, including while a model call
   remains blocked. Late returns cannot replace terminal state. Explicit retry
   cannot start until the previous owner releases its lock.
7. Start one bounded recovery consumer with AgentBridge. Operator CLI can inspect,
   cancel and explicitly retry tasks; uncertain effects require acknowledgement.
   No model tool receives authority to approve its own uncertain retry.

## Work and owners

- Store worker (Terra 6.1): `agent/recovery/store.py` and store tests; transactional
  submission/idempotency, attempts, locks, receipts and reconciliation.
- Runtime worker (Terra 6.1): `agent/recovery/runtime.py` and runtime tests; frozen
  restricted envelopes, restore validation, attempt execution and cancellation.
- Lead: tool gateway receipts; subagent/local delegation integration; bootstrap
  consumer and operator CLI; process interruption tests, docs and final validation.
- Luna: bounded path mapping; later fixture migration only if necessary.
- One independent review after integration: recovery/data integrity and isolation
  preservation need cross-component reasoning.

## Acceptance evidence

- Two processes contend for one task: only one executes; completed idempotent
  resubmission returns its durable result.
- Kill a real fixture process before a mutating tool: a new service recovers it.
- Kill after intent/before result, including after a real file write: the new
  service leaves needs_review and does not repeat the write.
- Explicit acknowledged retry is recorded as a new attempt, with old receipts
  retained. Unauthorized/no-ack retry fails.
- Cancel/timeout and late completion preserve original provenance and stop later
  tool execution; no concurrent retry while the old worker owns the task.
- Store errors deny dispatch/effects. Current authority/model changes deny or
  narrow restoration; private state and registry boundaries stay enforced.
- Actual temporary worker and local peer paths produce durable task IDs/results.
- Existing SQLite, EFFICIENCY and ISOLATION regression selection stays green;
  native Windows/browser skips and ChannelsPage baseline remain explicit.

Focused commands will use `.venv/bin/python -m pytest -q tests/test_recovery_*.py`.
Final integrated selection reuses `docs/isolation-001/run_regression.py` with new
recovery tests added in a RECOVERY receipt; no unnecessary live provider calls.
