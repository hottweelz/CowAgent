# RECOVERY-001 engineering review

One independent Sol 6.1/high review checked interruption boundaries, runtime
integration and authority preservation. Cross-process data integrity required
more than a routine file review. The reviewer ran the initial focused suite
(16 passed) and reported two P1 findings. The lead verified the fixes; no second
broad review or independent final approval is claimed.

| Finding | Fix and regression evidence |
| --- | --- |
| A startup consumer could bypass the caller's process-local delegation lock. | Every delegate claim now holds a cross-process receiver/session lock through worker cleanup. Store tests use separate spawned processes; the delegation timeout test runs the real recovery consumer while the first worker is closing and proves the follower remains queued without an attempt. The runtime waiter also retries its claim after the resource owner exits. |
| Restoring the default Agent incorrectly applied profile model pins that normal execution ignores. | Snapshot and restore use the strict current registry's default identity. Default Agents retain global routing and solo session overrides; group and delegate runs ignore session pins. Tests compare the restored adapter's actual model/provider resolution. Configured fallback behavior is retained. |

The lead also fixed three related in-scope findings:

- A disabled subagent setting now rejects queued work before model execution.
- A failed tool receipt latches the attempt guard. A real first file write can
  remain visible, but a second write is denied and the task needs review.
- Delayed timeout callbacks carry the attempt ID. A callback from an old failed
  attempt cannot cancel a queued or running explicit retry. A regression invokes
  the captured runtime callback after both retry transitions.

Process tests kill a private fixture before a write, after committed intent,
and after the real write but before the outcome receipt. A fresh recovery
service automatically handles only the first case. The other two require an
acknowledged retry. Another service restart does not replay completed work.

The public subagent tool test exercises real task admission, Agent streaming,
the restricted native Write gateway, committed receipts and the returned task
ID. A failed admission starts no model call. Local delegation tests retain the
native model/executor and actual durable result, rather than private-history
initialization. Production data and providers were not used.

Residual limits are documented in the operator guide. This is a trusted-host
restricted worker facility, not an OS sandbox, distributed lease service,
partial model checkpoint, or exactly-once side-effect protocol.
