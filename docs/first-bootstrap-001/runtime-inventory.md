# Legacy runtime inventory — source and metadata findings

**Scope:** source/configuration investigation only. This does not identify the
code loaded by PID 28093 or prove that the process is idle. Fresh process/listener observations are in [live-metadata.json](live-metadata.json);
pCloud coverage is in [pcloud.json](pcloud.json). No private prompt,
memory, credential value, or log content was read.

## Evidence boundary

The checked out candidate is PR #5 executable source `005c1e4805c75017467b817baa2a8bbbe3f7511d`
(the branch HEAD is a later documentation commit). The prior packet
[`service-drain.md`](../bullgod-discovery-002/service-drain.md) records a
controlled disposable rehearsal and supported component coverage. It explicitly
does not retrofit PID 28093. The loaded commit remains **unattested**.

Allowlisted metadata was read from `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData/config.json`
and `/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace/agents/team.json`.
The former has `channel_type=web`, `self_evolution_enabled=false`,
`mcp_tool_retrieval_enabled=false`, and `agent_workspace` set to the latter root.
That team roster has enabled IDs `default`, `testpilot`, `testpilot2`. A second,
non-configured test-data workspace roster has only `default` and `testpilot`;
it is not the workspace selected by the configured path. No values for
credential-bearing keys were read. No `mcp.json` was present under the
configured runtime workspace or its agent workspaces. The scheduler global and
legacy per-agent task paths were absent by file existence checks. The source-mode
plugin store at `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/plugins/plugins.json`
has 9 entries: 7 enabled (`cow_cli`, `Godcmd`, `Keyword`, `Banwords`, `linkai`,
`Role`, `Finish`) and 2 disabled (`Dungeon`, `Hello`). Source-mode plugin paths
are relative to process CWD (`plugins/plugin_manager.py:20-35`); the lifecycle
lead confirmed PID 28093's CWD matches the primary checkout. These are configuration/path
observations, not proof of process initialization or in-memory state.

The separate read-only receipt [`durable-metadata.json`](durable-metadata.json)
records four SQLite databases by schema and aggregate counts only. It found
global memory metadata with 13 sessions, 39 messages, and 18 runs (11 `done`,
7 `failed`); each of two per-agent memory indexes had one file and one chunk.
The recovery journal had 2 completed tasks, 2 completed attempts, no effects,
and 2 verifications, with zero completed attempts lacking current verification.
The three memory DBs had WAL and SHM sidecars at capture; the recovery DB did
not. This is a timestamped structural observation, not proof there is no active
work in PID 28093 or an open write transaction.

## Producer and admission inventory

| Producer / path | Configured / initialized / active certainty | Existing admission or observation | Durable unfinished work and SIGTERM | Finding / missing evidence |
| --- | --- | --- | --- | --- |
| HTTP web requests and streamed responses | `web` configured; source auto-adds web by default (`app.py:832-847`). PID 28093 currently owns 9899 and health is 200; the checkout bytes loaded by it are unknown. New PR #5 coordinator accounts handler and iterable completion; old process has no coordinator. | No old-process global close. Web server can be stopped only through channel manager (`app.py:314-352`); this is not a demonstrated operator drain route and does not fence other roots. | Live HTTP requests are in-memory; persisted chats do not reveal them. SIGTERM saves `user_datas.pkl` then exits; it does not wait for request completion (`app.py:493-503`). | Need verified ingress block and active-request census for the old process. Health alone is insufficient. |
| Chat queues, callbacks and native agent turns | Web is configured; initialization and activity are unverified. Source launches channel startup threads and may start plugin/cloud work in `ChannelManager.start` (`app.py:203-300`). | No legacy aggregate admission switch. Source only provides internal fresh-start drain; web/chat are tracked under PR #5. | Conversation state may persist while turn/callback/future remains live; rows cannot identify all in-flight work. SIGTERM does not join these activities. | Need old-process thread/queue/future inventory and per-turn state, plus exclusion of new clients. |
| Direct and parallel agent work / child futures | Team metadata enables three agent identities, not evidence that each Agent instance is initialized. PR #5 records synchronous scopes and owned child leases; task command path also exists (`app.py:835-841`). | Internal new coordinator is only installed by authenticated fresh startup (`common/service_lifecycle.py:1-5,17-33`); no old-process API. | Durable task/recovery rows do not cover every detached future or external action. SIGTERM has no join/accounting. | Need process-owned execution inventory and child-process/worker census. |
| Scheduler scan, scheduled callbacks and manual runs | Runtime global `workspace/scheduler/tasks.json` and legacy `workspace/agents/{default,testpilot,testpilot2}/scheduler/tasks.json` paths were absent by file-existence checks. `AgentBridge` still eagerly initializes scheduler (`bridge/agent_bridge.py:654-663`), whose single global store is resolved by `common/state_dir.py:213-228`; callback execution occurs in `scheduler_service.py:92-125,138-200`, and manual run starts a thread at `:200-246`. | No supported old-process pause/close control established. PR #5 tracks scheduler callbacks only in a newly instrumented process. | No task files at source-resolved paths, but in-memory tasks/callbacks and any alternate root remain unknown. SIGTERM can interrupt callback. | The data/workspace roots are confirmed. In-memory callback status remains unavailable; the scheduler GET path can lazily create/migrate a store and was not invoked. |
| Recovery and verification workers | Source starts recovery service during AgentBridge initialization (`bridge/agent_bridge.py:644-652`); whether that completed in PID 28093 is unknown. The current journal has two completed/verified tasks and no recorded effects or pending states; in-memory worker state is unknown. | No old-process pause/aggregate close. New source has recovery tracking; service uses daemon thread and worker pool (`agent/recovery/service.py:81-114`). | Recovery journal statuses and verification counts were read without task bodies; lock ownership and transient worker state are not established. `close()` joins only bounded time then pool shutdown (`:99-103`); signal handler does not call it. | Current counts show terminal history, not an empty journal or absent asynchronous work. No process-owned active-worker observation is available. |
| Self-evolution scans and work | Config says `false` in the selected data config; source nevertheless starts an idle trigger during AgentBridge init (`bridge/agent_bridge.py:665-670`). The trigger checks config before scans (`agent/evolution/trigger.py:97-129`). Initialized/active state is unknown. | No old-process pause control established. New drain tracks evolution only in its instrumented process. | Enabled state is off per current metadata, but a prior config reload or runtime override cannot be excluded without process-bound config evidence. Any already-running action may write/publish. SIGTERM does not join it. | No current active-evolution proof. Do not treat off flag as proof of no pre-existing work. |
| MCP servers and MCP tool calls | No `mcp.json` found in checked runtime roots and selected data config has no `mcp_servers` key. Source calls MCP warmup at ordinary server startup; configured servers spawn background loading (`app.py:545-572,853-857`; `agent/tools/tool_manager.py:353-403,508-530`). Actual in-memory ToolManager state unknown. | No legacy close control. PR #5 explicitly marks nonempty MCP runtime unsupported/untracked (`tool_manager.py:382-397`). | MCP calls/processes can outlive the initiating turn; client shutdown exists but signal path does not invoke it (`tool_manager.py:848-851`). | “No config found at checked paths,” not “MCP inactive.” Need actual runtime-config path confirmation and child-process census. |
| Plugins and plugin event callbacks | Source-mode store `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/plugins/plugins.json` contains 9 configured entries: 7 enabled (`cow_cli`, `Godcmd`, `Keyword`, `Banwords`, `linkai`, `Role`, `Finish`) and 2 disabled (`Dungeon`, `Hello`). Lifecycle lead confirmed PID 28093's CWD matches this checkout. `app.py:250-260` calls load/activate on first channel start, but the process's initialized/active instances are unknown. | No comprehensive old-process plugin admission or callback counter. New drain marks extension coverage unsupported (`common/service_lifecycle.py:11-13`; prior packet). | Enabled plugins may handle events, start threads, or perform network/process effects. No signal shutdown/join protocol established. | Configured flags do not prove which plugins finished initialization or have active callbacks. |
| Web browser / shell / subprocess and external adapters | Browser and shell tools exist in source; config alone does not establish invocation. MCP can spawn `npx`/`uvx`; cloud is conditional on `use_linkai` plus deployment ID (`app.py:261-275`). No descendant process or established TCP connection was observed at capture. Detached or remote adapter state is not proved by this snapshot. | PR #5 packet excludes browser/shell/cloud/external from positive drain; no old-process global boundary. | Child process or adapter work can continue beyond parent request. SIGTERM handler does not explicitly reap/settle these. | The process tree is observed; independently detached or remote actions remain outside it. No adapter was contacted. |
| Memory sync, knowledge, skill/asset maintenance | Runtime workspace has global and per-agent memory DB/WAL/SHM pathnames and skills/knowledge trees (names only). Agent initializer starts memory sync thread (`bridge/agent_initializer.py:948-966`); startup syncs built-in skills and scaffolds assets (`app.py:849-852`). Aggregate schema/counts are in [`durable-metadata.json`](durable-metadata.json). Actual open DBs and pending sync unknown. | New coordinator tracks memory only in fresh owner; no legacy barrier. | The three memory DBs had WAL/SHM sidecars at the metadata receipt time. Aggregate DB status does not show open handles or in-memory work. Skills sync can replace managed directories (`app.py:581-610`); signal save affects pickle. | Need consistent checkpoint/backup and read-only connection/maintenance status checks from parent. |
| Additional channels and timers | Selected config says web; selected runtime roster has no `channel_instances` key per metadata output. This is weaker than live channel registry evidence. Source otherwise accepts multiple legacy channel types (`app.py:61-116,832-847`). Timers exist in recovery/guest/native adapters. | Channel manager can stop named channels but no atomic cross-producer close. PR #5 flags non-web ingress unsupported (`common/service_lifecycle.py:26-33`). | Channel threads are daemon threads; some stop paths wait five seconds or interrupt a thread (`app.py:314-370`). SIGTERM path does not invoke `ChannelManager.stop`. | Need actual initialized channel registry, external ingress block, and timer/child census. |

## Quiescence and bounded uncertainty

The integrated decision is **C — UNBOUNDED RISK / NO-GO**. Current metadata
shows no recorded pending recovery work, no observed descendants/connections,
web-only channel configuration and evolution off. No scheduler or MCP files exist
at the resolved paths. Seven plugin enablements do exist, and their candidate
fixture returns `plugin_runtime_untracked`.

Class B remains a concrete future option: an operator-controlled interval must
exclude every client and automation, retain exclusion through recovery, accept the
specified unobservable transient work, and qualify a consistent private checkpoint.
That policy is neither established nor accepted now. Read-only metadata cannot
substitute for it. It also cannot clear the candidate plugin blocker. There is no
legacy quiescence receipt and no positive Class A claim.

## Exact source anchors

- Startup sequence and auto-channel selection: [`app.py`](../../app.py:821)
- SIGINT/SIGTERM only save `user_datas.pkl`: [`app.py`](../../app.py:493)
- Scheduler and recovery startup: [`bridge/agent_bridge.py`](../../bridge/agent_bridge.py:644)
- Evolution trigger: [`agent/evolution/trigger.py`](../../agent/evolution/trigger.py:97)
- MCP asynchronous warmup: [`agent/tools/tool_manager.py`](../../agent/tools/tool_manager.py:353)
- Plugin configuration discovery and activation: [`plugins/plugin_manager.py`](../../plugins/plugin_manager.py:121)
- Fresh-process-only lifecycle: [`common/service_lifecycle.py`](../../common/service_lifecycle.py:1)
- Prior test coverage and exclusions: [`service-drain.md`](../bullgod-discovery-002/service-drain.md)
