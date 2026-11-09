# Controlled service update and discovery invocation plan

Historical reviewed plan from preparation commit `17409b90`. DISCOVERY-002S now
implements its inactive hook; current qualification is in the
[acceptance audit](startup-acceptance.md) and [concrete packet](startup-maintenance-packet.md).
This original plan does not grant live execution authority.

Status: **PLAN ONLY — NOT AUTHORIZATION TO EXECUTE**.

The maintainer selected a verified plan only. This preparation does not install
an invocation hook, stop/restart CowAgent, change ownership or permissions,
refresh authority, invoke a model, dispatch work, or merge PR #4. The discovery
architecture remains unchanged. The later maintenance operation needs its own
explicit authorization after its implementation and evidence are reviewable.

## Separate acceptance gates

| Gate | Required evidence | Current state |
| --- | --- | --- |
| P: service preservation | Quiescent old process; exact launch/data/config bindings; verified rollback artifact; post-update durable-state comparison and healthy replacement | Plan and disposable rehearsal only; no live update |
| I: authenticated internal invocation | Approved launch, private guarded request, actual initialized owner/PID/epoch, one invocation, no public route | Proposed startup hook; not implemented or installed |
| D: actual read-only discovery | Actual native identities/current config and independently checked decisions; expired authority retained; bounded observations; zero observer dispatch | Not run; depends on authorized P and verified I |
| M: hosted macOS validation | Successful macOS Python 3.13 run on exact tested source, exact test comparison and receipt | PASSED on source 209f4e0f; 6,043 passed, 39 skipped, 93 passing subtests |

Passing M does not pass P/I/D. A local macOS check must be labeled local, and
never replace M. PR #4 stays draft and unmerged until the required gates pass
and a separate integration decision permits merging.

## Pinned source and rollback limits

The implemented discovery source is
`209f4e0fd53aeb249914755a68a1956d9e6225a0`, tree
`00b14af2a2b2e0c54c5bf5cdee34d124e6501d35`. Its 345 focused tests and independent
review passed. Later branch commits before this plan change only documentation.

The fallback candidate is known-tested master
`f659349785acf98905901a5cc53921436a109dbc`. It has passing integrated/hosted
evidence in [the Gate A report](../bullgod-discovery-001/integration.md).
It is **not proven identical to the source loaded by the old Python process**.
The future approval packet must explicitly accept that fallback version. Neither
Git checkout state nor a file hash can reconstruct an old interpreter's loaded
objects, conversation cache or thread state.

The future launch-hook implementation will produce a new candidate commit.
Record its exact commit, full tree, changed source/helper hashes and checks
before requesting service-update approval. Do not silently treat checks for
209f4e0f as validation of new executable code. Preserve the existing receipts as
evidence for their exact source; rerun only checks required by the actual delta.

Code-only archives are prepared from pinned Git objects. Their manifests, import
checks and disposable rollback rehearsal are recorded separately. They contain
tracked source, not live configuration, credentials, memory or conversation data.
No source archive is a backup of live runtime state.

## Verified current service and unresolved launch details

The [lifecycle receipt](service-lifecycle-review.json) records the metadata-only
snapshot at 18:14:12 UTC on 2026-11-09. PID 28093 started at 18:22:09 UTC on
2026-11-08. Its parent chain is bash → login → Terminal → launchd. No CowAgent
launchd owner was found. The process runs `app.py` from the existing checkout;
`.cow.pid` is absent. `COW_DESKTOP` and its token are absent. The data-root
environment points to existing CowAgent-TestData and `VIRTUAL_ENV` to the
checkout's `.venv`. No secret values were captured.

The resolved executable is framework Python 3.13, but its original invocation
path is **not established**. A separate standard-library-only check proved that
invoking the framework executable directly uses the framework prefix, while
`.venv/bin/python` uses the virtual-environment prefix. `VIRTUAL_ENV` alone does
not select Python's dependencies. Thus no exact replacement command is verified;
do not copy the resolved executable into a restart command. Later preparation
must establish the original interpreter invocation and dependency resolution,
and securely preserve required inherited environment without reporting secrets.

Health returned 200/ok. Aggregate conversations remain 13 sessions and 39 messages;
global runs report 11 done and 7 failed. Recovery reports two completed tasks and
two completed attempts. Self-evolution is disabled by current configuration.
These facts do not prove in-memory quiescence. Known scheduler files are absent,
but due/active in-memory work remains unknown. The global conversation database
has the `testpilot` merge marker but lacks `testpilot2`'s marker. Allowlisted
secondary database aggregate queries failed closed. Migration completion is
unknown, not diagnosed as a defect. Drain and migration status are mandatory
abort gates before any future stop.

No current CLI/updater is a verified safe maintenance path for this process.
The CLI relies on the absent PID file, so start/restart can create a second
instance. Stop can escalate to SIGKILL. The web/CLI updater can pull source,
install dependencies and restart beyond this bounded operation. SIGTERM's
handler saves user data but does not itself drain active work.

Relevant unchanged startup/persistence source paths between fallback and 209f4e0f:
`app.py`, `config.py`, `agent/memory`, `agent/workspace`, and `cli`. This narrows
the source delta; it does not prove the old process uses either revision or that
its state is safe for restart.

## Authenticated internal invocation design

Use a **launch-owned, one-shot observer**. No HTTP handler, control socket,
model-facing tool or long-lived command server is required.

1. An explicitly authorized local operator launches the reviewed source using
   the existing service account and a bounded private observation request.
   Authentication is the existing local OS account plus the existing private
   file provenance contract, not merely a loopback address or a supplied UID.
2. Validate the request before `load_config()` or any startup mutation. Require
   canonical paths, safe ancestors, real UID equal to effective UID, owner/mode
   checks, an ownership-enforcing filesystem, exact schema, bounded size,
   deadline, one-use launch correlation and the approved source/helper manifest.
   A model task cannot supply these host facts. Keep the request outside the
   ownership-ignored volume. Do not copy old credentials to establish new trust.
3. Return the actual owner from normal `_warmup_scheduler()` initialization and
   pass it directly to `TrustedDiscoveryHost.from_initialized_runtime(owner)`.
   The observer must not call a lazy getter or construct an Agent/model/memory
   manager. Existing normal startup owns initialization.
4. Invoke the observer synchronously before `ChannelManager.start()`. Source-mode
   startup has this ordering today. Desktop mode warms asynchronously and must
   reject the initial maintenance option unless a separately reviewed design
   establishes equivalent ordering. Do not change deployment mode implicitly.
5. Invalid request, binding, replay, expiry, manifest or observer output must fail
   the launch with a nonzero exit before public channels start. `SystemExit`
   handling must be explicit: current `app.run()` catches ordinary exceptions
   and can return without a failing source-mode exit code.
6. Allow only bounded inventory/select/revalidate against configured existing
   bindings. Keep adapter contact disabled for the initial procedure. No task,
   model, enrollment, approval or credential mutation is allowed. Do not add a
   caller-context override. An absent trusted active caller remains unknown.
7. Produce one sanitized private receipt bound to request digest/correlation,
   real/effective UID, interpreter, new PID/start time, initialized epoch and
   measured source/helper manifests. Never publish request secrets, private
   paths, prompts or memory. Launch/source measurements are not a universal
   attestation of all code loaded by Python.
8. The startup hook must not register itself with the web router or tool registry.
   Requests arriving through existing HTTP/model interfaces cannot enable it.
   A normal launch with no maintenance request retains current behavior.

Proposed implementation surface for a **later** change: the small startup seam
in `app.py`, a bounded `agent/discovery/startup_observer.py`, a launch-only helper
and focused tests. This plan does not contain or claim those changes. No second
registry, policy engine, scheduler, credential system or evidence platform is
needed. Same-UID/root arbitrary code remains outside the existing application
trust boundary.

## Service-preservation preconditions

Before any future stop, an operator-approved maintenance window must establish:

- Exact old process identity: PID, start time, executable, arguments, working
  directory, service account and supervising process. Verify identity again
  immediately before signalling; never trust `.cow.pid` alone.
- Exact current data root, three workspaces, config/profile fingerprints,
  model/provider metadata, interpreter and relevant launch environment. Keep
  secrets out of reports. Any required secret/environment checkpoint needs
  explicit private handling in the later approval packet; none is captured here.
- No active chat/stream, executing scheduler job, queued/running/recoverable task,
  pending publication, unresolved verification, or imminent autonomous work that
  could resume during the observation window. Check all configured agents, not
  only the default. Inability to establish quiescence is an abort condition.
- Current schema/migration state and startup asset state require no unreviewed
  migration or overwrite. Do not change settings to make this precondition pass.
- All original files, recovery refs/artifacts and worktrees remain preserved.
  No unrelated application is modified. No ownership/remount operation is used.

Normal startup is not intrinsically read-only: it loads/migrates config and team
state, migrates conversations, synchronizes skills/assets and warms MCP. Normal
AgentBridge initialization starts recovery, scheduler and evolution services.
The signal handler also saves `user_datas.pkl`. A read-only observer does not
erase those effects. If required startup behavior conflicts with preservation
or zero-dispatch conditions, stop the preparation and resolve that exact issue
before requesting execution approval. Do not replace the runtime or silently
disable its services to produce a passing receipt.

The present no-private-memory-read boundary remains in force. Any consistent
backup of live data is a separate explicitly described operation requiring
approval; no live data backup is created by this plan. If source-only rollback
cannot safely preserve the actual schema/state, the update must not begin until
a reviewed consistent backup/recovery procedure is separately authorized.

## Ordered execution procedure — requires later approval

1. **Freeze the candidate and approval packet.** Finish the inactive hook,
   focused security/default-startup tests, independent boundary review and
   required source-specific CI. Freeze candidate, fallback, launch command,
   environment bindings, quiescence evidence, output paths, maximum outage and
   rollback trigger. Make the actual reviewed commands available to the operator.
2. **Close admission and drain through supported controls.** Arrange the agreed
   maintenance window and prove quiescence. A quiet log is insufficient. If there
   is no safe supported way to prevent new work during the window, abort before
   stopping the service; do not invent a live admission override.
3. **Stop the exact old process gracefully.** Recheck its identity tuple, then
   send the approved SIGTERM. Observe confirmed termination and port release.
   Do not use stock `cow stop/restart` for this step: it can force-kill after
   about three seconds. A shutdown deadline expiry must abort/escalate to the
   operator; it does not authorize SIGKILL or a second instance.
4. **Select the reviewed source without moving live data.** Use the approved
   release mechanism, preserve the original checkout/refs/untracked files, and
   retain the original working directory/data/workspace semantics. Do not simply
   unpack an archive over a live repository. The disposable release-switch
   rehearsal does not authorize repository relocation or a new service layout.
5. **Launch once with the verified interpreter/environment and private request.**
   The exact live command is frozen only after the hook exists and launch-manager
   requirements are verified. Never present an invented flag as currently usable.
6. **Verify I, then D.** Require a receipt from the new actual initialized PID,
   bound to the approved launch and epoch. Independently verify native IDs,
   configured/effective route distinctions, preserved private ownership and
   expired authority, proof/admission uncertainty, and current-state revalidation.
   A denied result is valid; a manufactured positive selection is not.
7. **Verify P and health.** Compare durable counts, identities/config/profile
   bindings and permitted metadata, identify normal bookkeeping separately, and
   confirm exactly one intended service listener. No live model/task is a health
   probe. Do not treat health HTTP 200 alone as acceptance.
8. **Close or roll back.** Resume ordinary service use only as covered by the
   approved window and accepted gates. Any failed binding, public exposure,
   unexpected work, data/config drift, startup failure or verification failure
   triggers the preapproved rollback procedure below.

## Rollback procedure and abort limits

- Confirm which process actually started and stop only that process using the
  approved graceful mechanism. Do not assume a stale PID identifies it.
- Restore the verified fallback **source selection**, preserving the same data,
  configuration, profiles, workspaces and environment. Launch once without the
  one-shot observation request, using the recorded compatible command.
- Verify expected fallback source, one new PID/listener, health and durable
  metadata. Keep all failed-candidate logs/receipts and original recovery evidence.
- Do not restore a stale database over intervening writes. Do not reverse
  migrations, reset Git forcibly, delete unknown files, or overwrite profiles.
  If safe source rollback is no longer compatible, keep the evidence and obtain
  the separately authorized data-recovery decision.
- Rollback restores a known-tested service version, not the old PID or all
  transient in-memory state. A failure to terminate or recover within the agreed
  window requires operator intervention; no automatic force escalation is allowed.

## Verification evidence and remaining prerequisites

This plan is checked against actual startup/stop source, sanitized current
service metadata, immutable code archives and a disposable source-only rollback
rehearsal. Those checks establish the stated mechanics and limitations. They do
not establish successful live update, authentication of an unimplemented hook,
or preservation of live memory across restart.
The [independent documentation review](service-update-review.md) passed with no
remaining actionable findings. It confirms the stated limits and prerequisites,
not readiness to execute maintenance.

The [source-only verification receipt](service-update-verification.json) records:

- Full Git blob/mode verification for candidate 209f4e0f (2,034 tracked entries)
  and fallback f6593497 (2,003 entries); code-only archive hashes are retained.
- Python 3.13.1 compilation of 1,156 candidate and 1,148 fallback Python files.
  Guarded imports passed in disposable HOME/data directories, with no `app.run`,
  Agent construction, service start or live-data access. Each import recorded and
  blocked one croniter/platform architecture subprocess probe before launch.
- An atomic disposable source-pointer switch fallback → candidate → fallback;
  the synthetic state sentinel and both source trees remained unchanged. This
  does not verify the actual checkout update path or backup/restore of live data.

The private retained bundles are identified by basename and digest in the receipts.
No live runtime data or credentials were copied. Verification used `git archive`
on pinned objects, full blob/mode comparison, standard compile/import checks and
a disposable pointer rehearsal. No product tests or hook code were added.

The [hosted completion receipt](in-process-hosted-completion.json) records the
successful targeted macOS attempt and preserves the two earlier acquisition
failures plus the already valid Linux/application results. The executable source
and workflow were unchanged. Hosted completion does not authorize maintenance.

Source references for the later implementation/review are
[`app.py`](../../app.py) (signal/PID 486–535, migrations 628–669, assets 708–791,
startup 794–854), [`process.py`](../../cli/commands/process.py) (PID/lifecycle
86–215 and restart relay 301–418), and
[`agent_bridge.py`](../../bridge/agent_bridge.py) (background services 643–670).
Current web authentication can allow access when the web password is disabled
(`channel/web/core/_common.py:355`); it is not reused as privileged startup proof.

Before execution approval: implement/test the inactive hook, resolve all actual
quiescence/launch/environment/backup requirements, freeze the executable command
and outage/rollback contract, and obtain source-specific validation. Then request
explicit approval for that concrete service update. Do not ask for or infer an
ownership change, enrollment refresh, model run, dispatch, merge or activation.
