# Startup and shutdown effect acceptance

This source review applies to executable `f59a6e91`, based on PR #6. It updates
the detailed [FIRST-BOOTSTRAP-001 matrix](../first-bootstrap-001/startup-effects.md).
Its older line numbers are historical; module/function names below define current
scope. Configured files do not attest the old process's loaded state. No live
startup/shutdown effects were authorized or executed.

| Path / timing | Effect and required acceptance | Evidence and remaining limit |
| --- | --- | --- |
| `scripts/discovery_startup.py`, `startup_observer.prepare_launch`, before app | Authenticate and durably consume private one-use request; verify source, UID, interpreter, data root and expiry. | Cold rejection/order tests; actual disposable owner and 371-file receipt. Claim remains consumed on failure; no approval refresh. |
| Optional `maintenance_control.prepare`, then `app.run` owner bind | Read-only preparation after launch authentication. After genuine owner initialization, write private locks/service descriptor and start observer; later write one-shot claims and receipts. | Auth, replay, stale epoch, concurrency and fsync tests; real separate CLI. Same-UID/root boundary; no human-presence proof. Ordinary startup stays unchanged. |
| `config.load_config` and PID claim | Read configuration/environment, normalize or migrate settings; create process marker and logs. | Selected path metadata only. Full environment is not exported. Accept exact config/log/PID writes before launch. |
| `app` team and conversation migration | Adopt roster/channels, create schema, copy legacy conversations and write merge markers; migration can have background work. | Three IDs and native four-DB fiction verified. Actual testpilot2 marker absent; actual private migration remains untested. |
| Agent initialization, memory sync and indexes | Open/create SQLite/index state, start sync and other initialized services. | Actual WAL metadata, native schemas and fictional continuity verified. Candidate drain tracks supported work; no claim every legacy transaction is idle. |
| Built-in skills and subagent scaffold synchronization | Replace managed skills and copy assets/scaffolding; can overwrite managed local files. | Full path membership inventoried; actual private content not copied/compared. Accept exact managed replacement set after private rehearsal. |
| Scheduler/recovery/evolution initialization | Start scanning/work pools; migrate scheduler stores; resume eligible work; evolution may write or call providers if enabled. | Files show no scheduler tasks, recovery terminal history, evolution off. In-memory/pending external work remains unknown. Native accounting tests pass; process fixture does not create scheduled/recovery tasks. |
| Plugin scan and seven constructors | Imports all nine installed trees including disabled packages; known constructors may create/repair plugin config, read catalog/word files and create helper objects. | Seven enabled startup succeeds. Exact source/class/handlers qualify known paths. Unknown/rescanned/failed imports and missing enabled registrations block drain. |
| Plugin callbacks and descendants | Local config/session/file changes, downloads, provider requests, child threads/futures and publication. | [Per-plugin matrix](plugins.md): local leases, known children through completion; remote image jobs, extensible CLI and plugin management remain sticky unsupported. No external effect rollback claim. |
| MCP/cloud and other configured channels | May launch external processes or network services. | Selected configuration is web only, no MCP source and cloud disabled. Unsupported enabled features remain blockers; new configuration needs review. |
| Browser open at web start | Can open a user browser outside desktop mode. | Rehearsal uses `BROWSER=true`; actual browser effect untested. Explicitly accept or suppress in the approved future environment. No provider/model/adapter call in rehearsal. |
| `app` signal handler and final cleanup | SIGTERM can overwrite `user_datas.pkl`; process exit can interrupt work. Control cleanup only stops its observer and retains audit files. | Owned legacy/candidate/unsupported/fallback processes exit 0. A signal is not drain; old PID has no coordinator. Require accepted interruption or qualified candidate drain before any authorized stop. |

Startup can write before observation and before the external listener becomes
healthy. The observer does not make startup read-only. The private backup set
must cover all these local writes, and the operator must reconcile remote effects
separately. The Class C gate remains until enforced legacy exclusion and actual
private recovery are qualified; accepting this table alone cannot repair either.
