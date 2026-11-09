# Candidate startup and shutdown effects

**Candidate:** PR #5 executable source `005c1e4805c75017467b817baa2a8bbbe3f7511d`,
with PR #4 dependency. This matrix is a source review, not a live execution
receipt. The current loaded source for PID 28093 is not attested. Startup effects
are not read-only. Entries marked configured below use only ID/boolean/path
metadata; they do not assert successful initialization in the live process.
Fresh process and durable aggregate observations are linked from the milestone README.

| Effect | Timing and source | Class | Configured / initialized / active | Acceptance or blocker |
| --- | --- | --- | --- | --- |
| Private startup observer and lifecycle coordinator | `app.py:801-816`; authenticated helper request is consumed before normal startup; `common/service_lifecycle.py:17-33` prepares and binds a new in-process coordinator before publication. | Expected durable one-use claim/receipt writes; unknown on partial failure (claim is never reusable) | This is candidate-only. Ordinary startup has no coordinator; it cannot retrofit PID 28093. | Accept only the exact reviewed one-use request, candidate fingerprint, owner PID, data root, expiry, and receipt validation. Do not claim it is a legacy-process control. |
| Config loading and normalization | `app.py:821-822`; `config.py:566-720`. Reads config/environment and may normalize defaults, apply migration, or write config; paths and secret values are outside this report. | Read-only + expected durable write / unknown on error path | Current selected data metadata reports web-only and evolution off. Selected environment and configured paths are confirmed in live-metadata.json; full effective in-memory settings remain unattested. | Review exact candidate config and launch environment. No config edits or model/provider changes are part of this work. |
| PID file claim and cleanup | `app.py:506-542`; called at `app.py:823`. Writes a PID file only if none/stale; removes it at exit only if it still names this PID. | Reversible metadata | Candidate behavior. Current PID file state not checked by this worker. | Accept the candidate PID metadata write and cleanup. Verify the file path, current owner, and port/PID before a later launch. |
| Team roster migration/adoption | `app.py:652-660,824`; `agent/team.py` migration/adoption routines. | Reversible metadata + unknown | Data config points to runtime workspace; metadata there shows three enabled IDs. Candidate may migrate legacy roster and adopt channels. Live old-process source/config not attested. | Compare roster IDs and raw structural hashes on a disposable copy; preserve profiles. Require explicit acceptance for any roster write. |
| Conversation schema and merge migration | `app.py:662-675,825`; `agent/memory/conversation_store.py:2952-3065`. Synchronous global schema preparation, then other-agent copy can run asynchronously and records merge markers; startup docs note marker addition for a secondary agent without conversation tables. | Expected durable write + reversible metadata; potentially destructive only if source/destination incompatibility or interrupted migration | Runtime workspace has three enabled agent IDs; presence of DB pathnames/WAL/SHM was observed, not row content, schema, open state, or migration completion. | Backup must be SQLite-consistent and tested against a disposable copy. Compare schemas/counts/marker metadata, not message contents. Source rollback does not undo DB writes. |
| Agent indexes, memory DB, first Agent initialization and memory sync | `bridge/agent_bridge.py:641-675`; `bridge/agent_initializer.py:934-966`. AgentBridge starts recovery/scheduler/evolution; initializers may open/create memory indexes and start a sync thread. | Expected durable write + external/unknown (sync source dependent) | Three configured agent IDs do not establish which Agent objects are initialized. Memory DB/WAL/SHM pathnames exist in runtime workspace; no DB contents were read. | Accept index/schema/open-marker writes only after a private copy rehearsal. Establish source-side sync behavior and no in-flight sync. Existing PR #5 rehearsal did not exercise model or memory-turn behavior. |
| Built-in skills synchronization and subagent scaffolding | `app.py:581-610,678-798,849-852`. Built-in skill dirs are removed/re-copied for enabled Agents; subagent assets are copied only when enabled and absent. | Potentially destructive managed-file replacement + reversible metadata | Runtime workspace has skill and agent dirs; exact content was not read. Feature/config state was not fully established. | Compare names, hashes and permissions on a disposable copy. Require acceptance of managed-skill replacement. Do not treat as read-only startup. |
| Scheduler initialization, migration and scans | `app.py:625-632,867`; `bridge/agent_bridge.py:654-663`; `agent/tools/scheduler/integration.py:249-309`; `common/state_dir.py:213-228`; `agent/tools/scheduler/scheduler_service.py:92-200`. Starts background scanning and may migrate legacy per-agent stores; manual/due callbacks can run. | Durable write + external effect + unknown | Global `workspace/scheduler/tasks.json` and legacy `workspace/agents/{default,testpilot,testpilot2}/scheduler/tasks.json` paths were absent by file-existence checks. Scheduler initialization is coded to run eagerly. Live in-memory schedules and callback status unknown. | Confirm the exact live root; perform only metadata-only pending/running census. Startup must be delayed or callbacks fenced until reviewed; absent files do not prove no in-memory work. |
| Recovery and verification dispatch | `bridge/agent_bridge.py:644-652`; `agent/recovery/service.py:81-114`. Starts daemon scan and worker pool; can resume unfinished task attempts. | Durable write + external effect + unknown | Recovery DB and lock pathnames exist under runtime workspace. Metadata shows two completed tasks/attempts and current verifications, no effects or pending rows; lock ownership and active workers remain unknown. | Structural counts/status are in durable-metadata.json; they do not certify active-worker completion. Treat any pending/uncertain attempt as blocker until reviewed. SIGTERM does not close this service. |
| Evolution trigger | `bridge/agent_bridge.py:665-670`; `agent/evolution/trigger.py:97-145`. Starts a daemon idle-scan thread; if enabled it can run review, persist memory/skill changes, or follow up. | Durable write + external effect + unknown | Selected config metadata says disabled; initialization still starts the trigger, whose loop reads the setting. A previously loaded or runtime-updated value is not proven. | Current off flag is useful but insufficient to exclude already-running evolution. Establish runtime config and active scan/turn state; require no active run. |
| MCP initialization and child processes | `app.py:545-572,853-857`; `agent/tools/tool_manager.py:353-403,508-530,848-851`. Configured servers are loaded asynchronously and may spawn `npx`/`uvx` or connect remotely; shutdown method exists but is not called by normal signal wrapper. | External effect + unknown | No `mcp.json` found at the inspected data/workspace paths; config metadata had no `mcp_servers` key. This is not evidence of ToolManager state or other path resolution. | Confirm actual config source and runtime children; nonempty MCP remains outside supported positive drain. No external startup contact is accepted by this source-only review. |
| Plugin loading and activation | `app.py:250-260,877-879`; `plugins/plugin_manager.py:20-35,121-140,182-230,236-262,300-324`. Imports plugin modules, resolves enablement, constructs enabled classes, and registers their event callbacks. | Reversible metadata + external effect + unknown | Confirmed source-mode CWD matches primary checkout. Its `plugins/plugins.json` has 9 entries, 7 enabled (`cow_cli`, `Godcmd`, `Keyword`, `Banwords`, `linkai`, `Role`, `Finish`) and 2 disabled (`Dungeon`, `Hello`). This is configured state; whether all seven constructors completed in PID 28093 and whether callbacks are active is unknown. | Constructor details: CowCli builds aliases; Godcmd reads/repairs its config and may write `plugins/godcmd/config.json`; Keyword reads or creates `plugins/keyword/config.json`; Banwords reads or repairs `plugins/banwords/config.json` and loads its word list; LinkAI reads plugin config and creates Midjourney helper state; Role reads role files; Finish registers command handling (`cow_cli.py:97-101`; `godcmd.py:188-225`; `keyword.py:26-46`; `banwords.py:28-71`; `linkai.py:23-35`; `role.py:44-83`; `finish.py:20-23`). Enabled callbacks can perform network/file/thread work when events invoke them; e.g. Keyword downloads matching URL content, CowCli commands may contact the skills hub or start worker threads, and LinkAI handlers may call remote endpoints (`keyword.py:51-95`; `cow_cli.py:1180-1236,1576,1775`; `linkai/utils.py:53`; `linkai/summary.py:32-49`; `linkai/midjourney.py:206-299`). Constructor success is not proof that any callback is idle. |
| Cloud and other network startup | `app.py:261-275`; cloud starts only if `use_linkai` and a deployment ID are configured, and is launched in a daemon thread. MCP and plugins may also reach external services. | External effect + unknown | Selected file flag `use_linkai` is false; no cloud deployment identifier is present in the inspected config/environment. Effective loaded config remains unattested. | No cloud, model, provider, adapter, or approval action is allowed by this investigation. Confirm booleans and deployment-ID presence without printing values before any future launch. |
| Browser, shell, subprocesses | Web channel startup calls `webbrowser.open()` outside desktop mode (`channel/web/core/channel.py:1599-1607`). Tools and adapters also have process launch paths: MCP (`agent/tools/mcp/mcp_client.py`), browser (`agent/tools/browser/browser_service.py`), Codex (`agent/external/codex_client.py`). | External effect + unknown | Configured web channel implies the browser-open branch is reachable if `COW_DESKTOP` is not `1`; the selected environment confirms non-desktop mode. Actual browser launch was not exercised; the fixture uses BROWSER=true. Tool availability does not prove invocation. | Rehearsal used `BROWSER=true` per prior packet; that suppresses one browser launch only. Accept or explicitly suppress browser launch in the reviewed candidate environment; inspect descendants and adapters before the live window. |
| Logging and startup diagnostics | `common/log.py:35-60`; app startup and services log extensively. Startup observer has cold-auth constraints recorded in project memory and prior validation. | Expected durable write + unknown | Candidate startup creates/appends runtime log after its configuration/data root is selected. Resolved data root is confirmed; log contents were not read. | Accept bounded log creation/append as a durable effect; do not expose log content in evidence. Do not let pre-auth imports initialize logging before observer validation. |
| SIGINT/SIGTERM and user-data persistence | `app.py:493-503,827-830`; `config.py:422-447`. Handler logs, overwrites `user_datas.pkl`, then delegates to prior handler or exits. It does not close admission, stop channels, wait for handlers/futures, join recovery/evolution/scheduler threads, or shut down MCP. | Expected durable write + unknown interruption | This is source behavior of candidate; loaded behavior in PID 28093 is unverified. A pickle may be updated on shutdown. | Explicitly accept pickle save and its interruption risk only after a backup. SIGTERM is not a graceful drain and cannot justify quiescence. No SIGKILL/force escalation. |

## Source-mode preservation path map

- `config.py:get_data_root()` uses `COW_DATA_DIR` when set and otherwise the
  process working directory (`config.py:947-960`). The selected source config
  does not define `appdata_dir`, so `get_appdata_dir()` resolves to that data
  root (`config.py:972-977`). This holds `config.json`, `user_datas.pkl`, and
  `run.log` (`config.py:948`); only the file names and paths are used here.
- The selected `agent_workspace` resolves the workspace tree. Preserve global
  and per-agent memory databases with any WAL/SHM sidecars, recovery journal and
  locks, agent identities/profiles, knowledge, skills, and scheduler paths.
  The aggregate SQLite schemas/counts and sidecar presence are recorded in
  [`durable-metadata.json`](durable-metadata.json); it does not contain row
  bodies.
- Source-mode plugin storage is CWD-relative `./plugins` (`plugin_manager.py:20-35`),
  so preservation includes the configured `plugins/plugins.json` plus plugin
  directories and any per-plugin files they read or write. Do not publish
  private plugin configuration values.
- The CLI PID marker is `get_project_root()/.cow.pid` (`cli/commands/process.py:37-38`).
  It is reversible process metadata; confirm ownership before replacing/removing.
- The operator approval journal is not initialized by ordinary application
  startup. Preserve any private authority journal in place; do not read approval
  contents, copy it into Git, or refresh it. Current adapter enrollment/public
  binding metadata is handled by the lifecycle lead.

## Shutdown conclusion and bounded acceptance

The candidate's normal SIGTERM path is not an orderly service drain. It writes
`user_datas.pkl` and follows Python signal/exit behavior while daemon threads,
channel threads, child processes, network actions, or SQLite transactions may
still be active. The PR #5 internal drain can close admission and account for
enumerated components only after authenticated fresh startup and only for
supported coverage. It is not installed in PID 28093 and the ordinary signal
handler does not call it.

The prior PR #5 disposable rehearsal supports the coordinator mechanics for its
declared web-only case: held fictional leases blocked drain, new web work was
rejected after close, and the settled receipt passed with all required components.
That receipt does not cover live old-process state, real model/provider work,
enabled extensions, MCP/cloud/browser/shell/external work, or untracked detached
work. The older startup and maintenance packet must not be reused unchanged.

For an operator-exclusion interval, the minimum source-backed boundary is:

1. Block all external clients at a reviewed upstream mechanism and keep that
   block active; the service itself has no legacy global admission switch.
2. Prove no known HTTP request, channel callback, scheduler/recovery/evolution
   task, native/parallel turn, memory sync, or subprocess/adapter action remains.
3. Record unresolved blind spots. If the process inventory, durable work census,
   or exclusion mechanism cannot be independently verified, risk remains
   unbounded and the transition is NO-GO.
4. Preserve a consistent private backup before migration-capable startup. A
   source rollback cannot reverse database/schema/merge-marker, skills,
   plugin-store, log, PID, or `user_datas.pkl` writes.
5. Require explicit owner acceptance of the effects above before a future live
   start. No effects were executed or accepted by this worker.

## Prior packet reconciliation

The existing PR #5 packet and rehearsal already document exact tested source,
startup observer, candidate/fallback mechanics and synthetic behavior. Their
acceptance must stay limited to those recorded conditions. This update adds
current allowlisted configuration significance and exact source effect anchors;
it does not refresh the live process fingerprint, backup qualification, launch
environment, or live quiescence. See
[`service-drain.md`](../bullgod-discovery-002/service-drain.md),
[`startup-maintenance-packet.md`](../bullgod-discovery-002/startup-maintenance-packet.md),
and [`startup-migration-drain.json`](../bullgod-discovery-002/startup-migration-drain.json).
