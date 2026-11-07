# RECOVERY-001: durable worker recovery

CowAgent records work for native temporary sub agents and local peer delegation
in a private recovery journal. The journal supports operator inspection,
cancellation, and explicit retry after interruption. It does not resume a model
at its last token or continue a chat or scheduled task.

## Recovery behavior

The journal is a separate SQLite database at
`<shared workspace>/memory/recovery/tasks.db`. It uses WAL mode and `FULL`
synchronous writes. New journal files use private directory and file modes
(0700 and 0600). The existing conversation and memory index is not migrated,
rebuilt, or used to store the frozen task input.

Keep the live journal and its lock directory outside file-sync conflict
handlers, as required by the [indexed-memory repair](../memory-sqlite-io.md).
Do not rename active database companions or remove lock files. Use SQLite's
backup API for a consistent backup artifact, rather than copying a live main
database alone.

Each task has an immutable execution envelope, a state, and one or more
attempts. An attempt records tool effect intents before tool execution and
outcomes after execution. The journal states are:

| State | Meaning |
| --- | --- |
| `queued` | Ready for the recovery service to claim. |
| `running` | An attempt owns the task lock and is executing. |
| `completed` | The attempt completed. This task is never replayed. |
| `failed` | The attempt could not complete, including when current configuration prevents recovery. |
| `cancelled` | An operator or caller requested a stop. |
| `timed_out` | The task's time budget expired. |
| `needs_review` | An interrupted attempt recorded mutating intent, or a tool receipt/guard failed. Inspect before retry. |

At service startup, reconciliation changes an abandoned `running` task with no
mutating intent to `queued`. The service runs it as a new attempt from the
frozen input. If any mutating intent exists, reconciliation sets `needs_review`
and does not dispatch the task. A completed task is not replayed. This rule
reduces duplicate effects; it cannot prove that an external effect happened
exactly once. A tool may have completed an effect just before the process
stopped and before its outcome receipt was written.

The service does not take a task from a live worker based on elapsed time. A
POSIX `flock` stays open for the full attempt, including while a provider call is
blocked. Local peer delegation also holds a lock for its target Agent and
session, so a second task cannot run concurrently against that same target and
session. Retry fails while the previous worker still owns the task lock.

Before a frozen task runs, CowAgent checks that the Agent profiles are still
enabled and that the current session, project, delegation roster/policy,
permissions, model, and fallback configuration still match. Current permission
grants are intersected with the frozen authority; they can narrow access but
cannot expand it. A disabled or revoked profile, changed model configuration,
missing project, or invalid current settings causes recovery to fail closed.
The service does not load a peer's private conversation history.

## Operator commands

Run commands from the CowAgent repository or installed environment. Replace
`AGENT_ID` with the task owner's Agent ID and `TASK_ID` with the UUID shown by
`list` or `show`.

```bash
python -m agent.recovery list --owner AGENT_ID
python -m agent.recovery show TASK_ID --owner AGENT_ID
python -m agent.recovery cancel TASK_ID --owner AGENT_ID
python -m agent.recovery retry TASK_ID --owner AGENT_ID
```

`list` returns task IDs, kinds, states, attempt counts, and reasons. `show`
returns the task envelope and attempt/effect history; treat its output as
private because it includes the task input. `cancel` records a stop request and
signals an active attempt at its next cancellation check. It cannot forcibly
stop a provider call that does not return.

Retry is allowed only for `failed`, `cancelled`, `timed_out`, or `needs_review`
tasks. A task with any recorded mutating intent requires an explicit operator
acknowledgement:

```bash
python -m agent.recovery retry TASK_ID --owner AGENT_ID --acknowledge-effects
```

This acknowledgement means the operator accepts that a prior effect may be
repeated. It starts a new attempt from the frozen task input and retains the
prior attempt receipts. It does not resume at the point of interruption. A
completed task cannot be retried. Restricted workers have no tool to approve
or initiate replay. The CLI is for trusted host operators; `--owner` selects and
checks the task namespace, not an operating-system authentication boundary.
Existing privileged full-access host sessions retain their host authority.

## Limits

- Recovery requires POSIX `flock`; unsupported platforms fail closed.
- Only native temporary sub agents and local peer delegation use this journal.
  Remote peer transport, chats, and scheduled task continuation are not
  supported.
- The journal stores task inputs and effect receipts, not model-token
  checkpoints. Recovered work starts a new model attempt from the frozen input.
- An effect outside CowAgent's receipt boundary may not be visible to the
  journal. There is no exactly-once guarantee for external effects.
- A journal read/write failure stops dispatch or the guarded tool effect. There
  is no untracked execution fallback.
- This change does not migrate or rebuild production databases.
- Deployment requires a controlled CowAgent restart. This implementation was
  verified with private fixtures; the production service was not restarted.
- To roll back code, first stop CowAgent and retain the journal and task
  artifacts. Older code cannot reconcile this queue. Inspect pending tasks
  before dispatching replacement work, to avoid duplicate effects.
