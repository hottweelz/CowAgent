# Bounded legacy transition policy candidate

**Execution gate: CLASS C — NO-GO. This is a proposal, not live authorization.**
The implemented controls qualify a future instrumented service. They do not
retrofit or prove quiescence of PID 28093.

## Pinned inputs and prerequisites

| Input | Qualified value |
| --- | --- |
| Candidate executable | `f59a6e91152900d709cad1775b2756cf25b316c0` |
| Candidate tree | `988926c42ab9638f129b6b0ea1970c99db0d447a` |
| Startup Python manifest | 371 files; SHA-256 `11e67da08cc9b5efa7b1f8220dbbe4ba26fe208c3b992a6bcae64f17e47a1279` |
| Base | PR #6 `fcbc0d25cbf86d9ff94d4dd9f7fd067a6b2d183b` |
| Tested fallback | master `f659349785acf98905901a5cc53921436a109dbc` |
| Existing primary HEAD | `a507a400985512683c870ef4fe059fa5982ad13e` |
| Legacy identity | PID 28093, start epoch 1794162129.482237; loaded source unknown |
| Service / disposable endpoint | `127.0.0.1:9899` / `127.0.0.1:19890` |
| Invocation | `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python` |

Before scheduling a live window, qualify the scoped OS admission mechanism in
[ingress.md](ingress.md), including new requests over existing keep-alive
connections. A cooperating gateway/client policy is insufficient because direct
loopback access succeeds. An approved private PF anchor is only a proposed
mechanism: it needs an existing active hook, effective loopback filtering and
disposable proof. Do not reload global PF rules, flush states, or infer that
approval makes an inert rule work. If those prerequisites fail, qualify a scoped
process-aware host policy separately. No rule has been installed.

The boundary must cover every listener route and local forwarder. It may block
HTTP health; use separately approved out-of-band PID/start/listener observation
during that interval. Keep an unrelated application canary working and prove
reversal. Existing in-flight requests may finish; further requests on their
connections must be excluded. Any bypass aborts the window before signaling.

## Background work and legacy interruption

External exclusion closes only new externally initiated work. Already accepted
HTTP/SSE/chat/native/parallel work, scheduler callbacks, recovery dispatch,
memory sync, evolution and plugin children may continue. Files show no saved
scheduler tasks and evolution disabled; these facts do not attest in-memory
queues or configuration. Seven plugin constructors do not independently start
workers, but accepted CowCli/LinkAI commands can have children or remote effects.
The [plugin matrix](plugins.md) identifies local completion and unsupported paths.

The legacy PID has no aggregate lease census or retroactive drain switch. A quiet
listener, no descendants, terminal DB rows or an elapsed wait cannot prove idle.
To support a later bounded policy, the operator must identify every known active
producer/effect, its completion evidence or exact accepted interruption and
reconciliation action. Unknown detached/plugin/remote activity stays a blocker.
The one-time risk would be loss of unobservable in-memory state and partial local
or remote work, not a fictional positive drain. It is not yet sufficiently bounded.

After all technical prerequisites and the exact interruption scope are accepted,
the proposed legacy stop is one identity-checked SIGTERM with a 30-second wait.
Timeout aborts; there is no SIGKILL, automatic retry or second service launch.
SIGTERM may save `user_datas.pkl`; it does not drain work. Confirm owned-process
exit and the listener is gone before any source selection or replacement launch.
No stop command was executed by this milestone.

## Private preservation and restoration

Use the [actual metadata manifest](live-state-manifest.json) and
[recovery procedure](recovery.md). The three roots are the selected data root,
selected runtime workspace and source-mode plugin directory. The unselected
workspace/reproduction directory is preserved separately pending classification.
Include the four actual SQLite roles, profiles/team/config, user data, scheduler
files if present, skills/assets and mutable plugin state. Reconcile unknown files;
do not discard or silently classify them as disposable.

A separate private operation must name the operator, source paths/data classes,
destination, access boundary, retention/deletion rule and isolated restore scope.
No actual private backup exists from this task. Never export credentials or memory
into Git/evidence, and preserve operator authority in place without rewinding
revocations or consuming approvals.

Per-database SQLite online backup provides transaction-consistent images while
WAL is active; it does not make four independent DBs and related files atomic.
Establish a closed application-write interval, capture a pre-transition recovery
set if required, then verify a final post-exit set before migration-capable startup.
Include shutdown pickle writes. Verify native schemas/integrity, manifest membership,
modes/symlinks and approved structural continuity in a new isolated directory.
Do not checkpoint, vacuum, change journal modes, copy live WAL/SHM as a backup,
or force-close connections. Actual private rehearsal must demonstrate the selected
snapshot procedure before treating the recovery prerequisite as qualified.

Keep the failed candidate tree and any later user data. Restore into a new private
destination, compare against both the snapshot and failed tree, and reconcile
later legitimate files/rows explicitly. Never overwrite the newer tree with an
old snapshot. Source fallback does not reverse migrations, file writes or remote
effects. Do not replay historical task/effect rows; reconcile uncertain remote
operations separately with their authoritative result, without automatic retries.

## Candidate source and private launch

The prior [source-selection procedure](../first-bootstrap-001/maintenance.md)
remains relevant only with this candidate/manifest and the new CLI path. Require
an initially clean tracked index/worktree and use both `--staged --worktree` for
the approved runtime paths. Verify the exact tracked Python path set and bytes
against the chosen commit; preserve original untracked/ignored files and refs.
Do not commit the staged deployment selection or equate HEAD with loaded bytes.

The source selection set is:

```text
app.py config.py agent bridge common models channel plugins
scripts/discovery_startup.py scripts/maintenance_drain.py
```

Use the original virtual-environment invocation, not its resolved framework
binary. The inherited production environment remains unexported; any later
capture must be separately authorized, remain in one controller's memory and
never appear in arguments, logs or evidence. Dependency and configuration changes
require renewed compatibility qualification.

Under a future authorized operation, prepare a fresh one-use authenticated startup
request for the exact manifest, UID, interpreter/prefix and data root. The existing
[request fixture](../first-bootstrap-001/request_fixture.py) demonstrates the
schema only; it does not create production authority. Use a new empty canonical
0700 control directory on ownership-enforcing storage. Do not reuse expired
requests, claimed IDs or old control directories. The external APFS ownership
policy is unchanged; do not bypass provenance checks.

The supported command forms, to be filled with approved private paths, are:

```sh
"/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python" \
  scripts/discovery_startup.py --request /approved/private/request.json \
  --control-dir /approved/private/new-control-directory

"/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python" \
  scripts/maintenance_drain.py --control-dir /approved/private/new-control-directory \
  --grant close-admission-and-observe --timeout 30
```

These forms were exercised on disposable state through the supported helper/CLI.
Do not run them on live state under this report. Startup may write or start
background work before the observer receipt: accept every effect in
[startup-effects.md](startup-effects.md) and preclude unexpected pending work first.

Verify health, three registered IDs, denied discovery/dispatch without authority,
exact manifest and matching service PID/runtime/coordinator binding. Retain the
private one-use claim and sanitized receipt. The first candidate drain acceptance
leaves admission closed even if it succeeds; there is no reopen operation. An
authorized production start after this closed acceptance needs another reviewed
launch and new request/directory, not a hidden reset of the coordinator.

## Subsequent drain and fallback

The control uses the existing trusted OS-account boundary, not human-presence
authentication. It accepts only explicit close-and-observe authority for its
initialized owner. Timeout is 0–60 seconds plus bounded delivery/publication;
it never cancels work, sends a signal, restarts or reopens admission. A later
explicit request with a fresh ID may observe actual completion. Same-ID retries,
stale bindings, unauthorized provenance and missing durable receipts reject.

A positive receipt requires admission closed, zero tracked work, all nine
components, fresh settled probes and no unsupported activity. Unknown plugin
imports/handlers, remote image jobs, extensible command/plugin-management effects,
or lost control integrity cannot be waived. Missing proof aborts fallback stop;
preserve the running process and diagnose the named blocker within authorization.

After a qualified drain and separately authorized stop, select the pinned master
fallback with both index/worktree restore and exact path verification. Master has
no new control; it needs its own reviewed launch/effects boundary. Select state
only after the isolated restore and later-data reconciliation. Verify identity,
health and durable continuity before restoring external admission. Reopening the
external fence is a separate operator action after all acceptance checks.

Immediate aborts: changed PID/start/source, bypassable ingress, unknown producer,
pending/uncertain effect, invalid private provenance, incomplete/corrupt snapshot,
unexpected startup writes, manifest mismatch, new lifecycle blocker, stop timeout,
occupied listener, or failed candidate/fallback health. Retain private diagnostics
without printing them. Do not escalate to force stop or delete newer state.

## Decisions still required

1. Authorize and successfully qualify the narrow OS fence on a disposable host;
   then separately approve its exact live application/removal and observation path.
2. Approve and qualify the actual private backup/restore scope, later-data retention
   and reconciliation; metadata inventory and fictional restoration are not this test.
3. Accept only specifically bounded legacy in-memory/background/external interruption
   risk after the remaining producers/effects have a credible observation/recovery plan.
4. Accept the enumerated startup/shutdown effects, private environment handling,
   exact candidate/fallback, outage bound and one live stop/start attempt.

APFS policy changes, authority refresh, BullGod production activation and PR merges
are separate decisions. None follows from this policy or from passing candidate CI.
