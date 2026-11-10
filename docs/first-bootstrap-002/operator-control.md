# Private operator drain control

The candidate implements `cow.maintenance.drain/1` for a future, freshly
instrumented service. PID 28093 has no such control. This work does not change,
signal, restart or prove the quiescence of that process.

## Enable at an authorized future launch

The operator must first create an **empty, canonical, absolute, 0700 directory**
on an ownership-enforcing filesystem, owned by the service's real UID. Its
ancestors must meet the existing trusted private-file contract. A Darwin volume
that ignores ownership is rejected even when its mode bits look correct.
Do not use the present external checkout as a trusted control location.

The existing authenticated launch helper accepts the optional `--control-dir`
argument. Startup-request authentication must succeed before control preparation.
After normal runtime initialization and lifecycle-owner binding, the application
publishes `service.json` and starts the private observer. Default startup does
not prepare a directory, publish a descriptor or start an observer.

Library integration:

```python
# After prepare_launch(request_path) succeeds:
prepared = common.maintenance_control.prepare(control_dir)
# After service_lifecycle.bind_initialized(coordinator, owner, channel_entries):
control = common.maintenance_control.bind_initialized(prepared, coordinator, owner)
# At application cleanup, stop only the observer:
control.close()
```

Binding requires the currently installed coordinator, its genuine initialized
owner, and the current process. The descriptor binds service ID, PID, real UID,
coordinator epoch and initialized-runtime epoch. All three epochs/IDs are fresh
random identifiers. A PID alone is never a target selector or liveness proof.
An old descriptor cannot bind a replacement process, even if the OS reuses its
PID. Each service launch requires a new empty directory; do not erase old claims
and reuse a prior directory.

## Explicit bounded invocation

For a future authorized service, run the matching interpreter and source:

```sh
python scripts/maintenance_drain.py \
  --control-dir /canonical/private/control-directory \
  --grant close-admission-and-observe --timeout 30
```

This is an example command, not permission to run live maintenance. There is no
PID argument, HTTP endpoint, chat command, model tool, shell execution, signal,
termination, restart, cancellation or admission-reopen action. Exit 0 means a
positive drain observation; exit 1 means a valid non-positive receipt; exit 2
means no trustworthy receipt. `--timeout` is 0 to 60 seconds. The CLI allows
five additional seconds for inbox delivery and receipt publication, then fails
closed. It never infers successful drain from a timeout or a missing process.

Authentication reuses the existing private OS-account boundary: real/effective
UID equality, owned canonical paths, trusted ancestors, ownership enforcement,
0700 directories and single-link 0600 regular files opened without following
symlinks. This is **not human-presence authentication**. Arbitrary same-UID/root
code is outside the application's existing trust boundary. Use OS account and
host controls if a distinct human approval boundary is required.

The operator explicitly grants only `close-admission-and-observe`. Every request
has a fresh ID, strict operation schema, service binding, issue/expiry times and
bounded timeout. Unknown operations, changed descriptors, stale epochs, expired
requests and invalid private provenance cannot close admission. File input is
bounded to 64 KiB. No secret token or provider credential is read or included.

## Ordering, replay and timeout

The CLI takes a nonblocking exclusive operator lock. A simultaneous operator
invocation rejects. It publishes a complete fsynced request atomically through
the single inbox. A separate private `io.lock` protects file publication and
reads across processes and threads. Writers hold an exclusive lock through the
temporary-file link, temporary-name removal and final directory fsync; readers
hold a shared lock. Each operation opens its own lock descriptor. Readers cannot
observe the temporary two-link state. A failed publication removes its final name
before releasing the exclusive lock. A reader also fsyncs the directory before
accepting bytes, so a writer crash after temporary-name removal cannot produce
an accepted but uncommitted name. Missing or failed persistence remains denial.
The I/O lock is created and fsynced during owner binding before `service.json`
is published; preparation remains read-only. I/O-lock contention has a bounded
five-second deadline.

The observer atomically links the inbox to an exclusive
`claimed-<request_id>.json`, removes the inbox and fsyncs the directory **before
closing admission**. It rechecks claimed bytes, descriptor and owner. Durable
claims are retained; an ID can run at most once. A replay cannot replace its
first receipt. A crash after claim but before receipt leaves an uncertain result
and a consumed ID. The operator may use a new explicit ID to observe the same
still-running owner; there is no automatic replay.

After authentication and durable claim, the observer closes admission before
calling the coordinator's bounded wait. It runs in a fresh execution context
and holds no admitted-work lease. This prevents a control request from waiting
on itself. Existing admitted parent/child, scheduler and recovery work retain
their leases through completion. A timeout reports their active category/agent
counts and leaves admission closed. It never releases leases or cancels work.
A later explicit request can obtain a positive result after actual completion.

Missing coverage, unknown detached plugin activity and unsettled probes remain
coordinator blockers. The control does not weaken `RuntimeDrain`. Loss of control
directory/file integrity or an observer I/O failure adds the sticky
`maintenance_control_unavailable` blocker and stops the observer. It does not
turn unauthenticated input into an automatic drain action.

## Receipt and preservation

The fsynced, immutable `receipt-<request_id>.json` contains only protocol, request
ID/digest, service binding, completion timestamp, fixed status, closed/drained
flags, public active category/agent counts, public blockers and required/registered
component names. It does not echo request content, exception text, private paths,
configuration, prompts or credentials. The descriptor, requests, claims, locks and
receipts remain 0600 under the 0700 directory. The request digest binds a receipt
to exact request bytes; it does not replace filesystem authentication.

Retain the directory as the per-launch replay/audit ledger. The implementation
does not purge receipts or claims. Exhausted disk space, unavailable directory
fsync, unsupported POSIX APIs and uncertain ownership fail closed. Linux/macOS
POSIX operation is supported; Windows rejects rather than weakening trust. No
actual private-state copy, backup, external adapter call or model execution is
part of operator drain.

## Verification

`tests/test_maintenance_control.py` exercises private provenance, unauthorized
effective UID, symlink/hardlink and permission rejection, ownership guard failure,
unbound owners, strict grant, stale PID/runtime/service epochs, expiry, replay,
concurrent operators, durable claim ordering, claim/receipt persistence failure,
timeouts, parent/child/scheduler/recovery accounting, unknown coverage, later
completion, sanitized errors and absence of exec/signals. Genuine initialized
owner and enabled-plugin service acceptance must also be demonstrated by the
parent integration rehearsal; unit fakes do not certify those lifetimes.

Separate-process reader tests pause publication immediately after its hardlink
and immediately before its final directory fsync. Both prove readers remain
blocked until commit. Fault injection also proves publication-fsync and
reader-fsync failures cannot return a positive receipt.
