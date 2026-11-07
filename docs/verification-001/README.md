# VERIFICATION-001: execution, acceptance and confirmed state

CowAgent reports three outcomes for durable temporary workers and local
delegation. A worker's final message cannot certify any check.

| Field | Meaning | Values |
| --- | --- | --- |
| `execution_status` | What happened to the worker attempt. | Existing lifecycle, including `completed`, `failed`, `cancelled`, `timed_out`, `needs_review`. |
| `acceptance_status` | Whether independent checks satisfied the supplied output criteria. | `passed`, `failed`, `unverified`. |
| `external_state_status` | Whether independent observation matched the specified state. | `confirmed`, `failed`, `unverified`. |

`completed` remains the execution terminal state. An acceptance failure does
not change it to `failed` or make it eligible for replay. `verified` is true
only when execution is completed, acceptance is passed and external state is
confirmed. It covers the supplied criteria, not unstated requirements inferred
from the task's prose. Criteria quality remains the caller's responsibility.

This first version supports native text/JSON artifacts. External-state checks
read filesystem state independently of the worker and its write receipt. They
do not confirm publication, delivery, remote database changes or another
external service. Unsupported checks remain `unverified`.

## Declare checks before execution

Both `subagent` and `agent_delegate` accept a `verification` object. A subagent
batch can set one per task. The caller supplies the criteria; the execution
envelope freezes them before dispatch. The worker cannot replace them after
seeing its result.

```json
{
  "goal": "Write result.json with answer 42 in the task workspace.",
  "verification": {
    "acceptance": [
      {"id": "answer", "type": "json_equals", "path": "result.json", "expected": {"answer": 42}}
    ],
    "external_state": [
      {"id": "saved-file", "type": "text_equals", "path": "result.json", "expected": "{\"answer\":42}"}
    ]
  }
}
```

For local delegation, use `agent_id` and `task` instead of `goal`. Paths are
relative to the worker's task/project directory; absolute paths still need a
read grant. Adding a check does not grant file access. Native checks are:

- `file_exists`: a readable, supported regular text file exists.
- `text_equals`: complete UTF-8 contents equal the expected string.
- `json_equals`: parsed JSON matches the expected value, preserving value types.
- `sha256`: the file's UTF-8 bytes match a supplied SHA-256 digest.

The existing file broker enforces read roots, private-state exclusions,
symlink/hard-link rules and the 2 MiB text limit. It cannot invoke a command,
model, plug-in or remote request. Criteria sharing a path reuse one independent
read in the same report. Evidence includes check IDs, outcomes, reason codes,
timestamps, content hashes and byte counts; it does not copy file contents.

Missing criteria are unverified. A mismatch or missing artifact fails the
check. Inaccessible files and unsupported checks are unverified. Known failed
mutations or permission refusals fail acceptance, including failures rejected
before tool execution. A matching pre-existing file can still confirm state
while acceptance fails because the requested write was denied. Failed ordinary
read attempts alone do not invalidate otherwise satisfied output criteria.

## Inspect and refresh evidence

```bash
python -m agent.recovery list --owner AGENT_ID
python -m agent.recovery show TASK_ID --owner AGENT_ID
python -m agent.recovery verify TASK_ID --owner AGENT_ID
```

`list` and tool results include all three outcomes. `show` includes the frozen
criteria, tool receipts and verification history. `verify` appends a new
read-only observation for a completed task. It does not run the worker, change
its attempt count, edit its execution result or permit replay. The CLI checks
the task owner and requires a completed, unlocked task. It is a trusted host
operator interface; `--owner` is not an OS authentication boundary.

Reports are stored in an additive table in the existing protected recovery
journal. Each report is tied to task ID, current attempt ID and a hash of the
frozen criteria. Old reports remain available after re-verification. A changed
artifact can therefore produce a failed newer report without erasing the
earlier observation.

The runtime commits execution completion before verification. If the process
stops in between, the recovery consumer runs only the missing read-only checks.
It never requeues the completed task. A verification storage failure leaves
the result unverified, reports the error, and permits a later read-only check.
Current authority must still permit observation; unavailable authority cannot
produce a passing check. Existing completed tasks without criteria receive
explicitly unverified outcomes.

## Limits and operation

- Confirmation is evidence at the recorded time, not a promise that a file
  remains unchanged. Separate files are not read as an atomic snapshot.
- Worker summaries remain untrusted text, even when they contain “verified.”
  A successful tool transport or a completed legacy run row is execution only.
- Remote-service confirmation, arbitrary executable validators, binary/rich
  documents and natural-language semantic grading are not included.
- Retain RECOVERY-001's POSIX and trusted-host boundaries. No OS sandbox or
  exactly-once effect guarantee is added. Keep the live journal outside file
  sync/conflict handlers as required by the SQLite memory repair.
- No production service or database was changed during implementation. Deploy
  with a controlled restart. For rollback, stop CowAgent and retain the journal;
  older code ignores verification records and reports execution only.

The [plan](plan.md), [review](review.md) and [verification receipt](verification.json)
record scope and evidence. The nine ChannelsPage TS2322 errors remain the
separate [open typecheck baseline](../known-issues/channels-page-typecheck.md).
