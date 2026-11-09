# BullGod admission, drain and transition preparation

The follow-up is isolated on `codex/bullgod-service-drain` in
[draft PR #5](https://github.com/hottweelz/CowAgent/pull/5), based on PR #4.
Executable source is `005c1e4805c75017467b817baa2a8bbbe3f7511d`, startup manifest
`210cece16670f2d7dc39e15eb8d2ea299388170f05f68710afd6968e7159f36f`.
The original checkout and PID 28093 on 127.0.0.1:9899 remain unchanged.

## Control and coverage

Authenticated fresh startup installs a process-wide coordinator before producers
start. It binds the normally initialized AgentBridge and registers supported
components. Normal startup without the private launch request keeps the existing
behavior. There is no HTTP/chat drain command, control server or retrofit of an
already running process.

`common.service_lifecycle.drain(owner, timeout)` closes admission atomically and
returns a process/epoch-bound receipt. New roots reject after close. Already
admitted work can reserve children only through a live canonical lease. Thread
and pool handoffs reserve before submission; cancellation of a parent does not
release a running child. Generator activation ends between yields. Timeout neither
cancels work nor reopens admission.

| Boundary | Completion accounted for |
| --- | --- |
| Web requests | Handler plus response iterable; only GET `/api/health` bypasses closed admission |
| Chat queues | Acceptance, queued handoff, worker, reply send and callback cleanup |
| Direct and parallel agents | Synchronous Agent/ChatService/AgentBridge scope; child futures remain counted after parent cancellation |
| Scheduler | Due scans and manual admission through callback and record updates |
| Recovery | Scan, queued futures, execution, timer cleanup and verification; unsettled/unverified durable rows block |
| Evolution | Scan and full execution, including writes and publication |
| Memory/knowledge | Migration, maintenance, flush, daily work, reindex and background sync |
| Startup | Initialization work and bounded HTTP preparation; existing managed listener must be ready |

Probes run only after a closed, zero-lease barrier. A generation change invalidates
the sample. Missing coverage, invalid owner, probe failure, active work or a sticky
unsupported-effect marker prevents `drained=true`. Empty persisted counts and
healthy HTTP are not substitutes.

Supported qualification used web-only ingress and disabled plugins, with no
MCP/cloud/browser/shell/external work. Non-web transport ingress, enabled plugins,
configured MCP, cloud activity, browser/shell descendants, remote adapter activity,
legacy/fallback model dispatch, direct detached XunFei/LinkAI work, web rebind and
selected external-process API actions explicitly block positive drain. This is
not a claim that those features cannot run; their work cannot yet be certified
by this bounded receipt. Unsupported markers do not silently clear.

## Verification

| Gate | Result |
| --- | --- |
| Focused tests | Worker and integrated selections pass; source handoff records exact selections without summing overlaps |
| Independent engineering review | Two findings corrected and cleared by targeted verification; no open findings in that review |
| Full protected local regression | [Passed](service-drain-local.json): 6,124 passed, 36 skipped, 93 subtests; zero failures/errors |
| Hosted Linux/macOS/application/lint | [All five jobs passed](service-drain-hosted.json), run 42699928448, no reruns |
| Actual owned-process transition | Passed; [durable receipt](service-drain-rehearsal.json) |

Hosted Linux 3.11/3.13 each passed 6,114 tests with 46 skips; hosted macOS passed
6,121 with 39 skips. Each has 93 passing subtests. All three jobs ran the same
6,160 named cases: 45 additions, no removals and unchanged exact platform skip
sets. The two earlier order-sensitive focused failures did not reproduce in the
full local directory run or any hosted platform. Source review cleared the stale
probe race and detached-provider coverage findings after their corrections.

The real disposable candidate PID 36746 bound port **19884**, authenticated its
one-use startup request, initialized the real owner and listed `default`,
`testpilot`, `testpilot2`. Two fictional held work leases kept drain false. After
closure a new message request returned 503 while health stayed 200. Releasing both
work items produced a receipt with no active work/blockers and all nine required
components. These work items did not execute a model or impersonate TestPilot.

After the successful receipt, the owned candidate exited gracefully with code 0.
The exact same-directory `git restore` of runtime paths selected fallback
`a507a400985512683c870ef4fe059fa5982ad13e`. Fallback PID 36755 returned health 200
and exited gracefully with code 0. Three fictional sessions/messages and zero
runs retained the same normalized row digest throughout; an unrelated sentinel
was preserved. The live PID and its port 9899 were unchanged. No forced kill,
model call, adapter contact or task approval was part of this rehearsal.

The private test controller uses an owned stdin pipe to call the internal control.
It is not installed into the product. This proves the control and process
mechanics, not the existence of an authorized invoker inside old PID 28093.

## Reviewed startup effects and transition limits

| Existing effect | Timing and consequence |
| --- | --- |
| Runtime log/config initialization and PID file | Starts after private request validation; may write logs/config/PID metadata before owner binding |
| Team adoption and conversation migration | Before channel admission; may migrate schema/copy rows/archive legacy tables and publish merge markers |
| Workspace skills/subagent scaffolding | Before channels; skills synchronization can replace managed assets, while scaffold files are seeded |
| Recovery/scheduler/evolution initialization | Before observer publication; configured due/resumable work can start and must be explicitly reviewed |
| Plugin initialization, MCP warmup, optional cloud | Can import extensions or launch network/subprocess work; unsupported coverage blocks successful drain |
| Browser launch for web console | Existing startup effect; the disposable environment used `BROWSER=true` to suppress a real desktop launch |
| First agent initialization | May create workspace/memory indexes, synchronize native runtime configuration, and schedule memory work; held-lease rehearsal does not claim a model/Agent-memory execution |
| SIGTERM user-data save | Existing shutdown behavior can write data after drain; this is a separate accepted shutdown effect, not new admitted work |

The earlier migration metadata says testpilot2 would receive a missing merge
marker with no conversation rows imported/deleted. It does not authorize the
write. The [prior maintenance packet](startup-maintenance-packet.md) remains
historical evidence for its pinned candidate; do not substitute this new source
or its request manifest without a new explicit maintenance decision.

Before a live window, the maintainer must authorize a concrete bootstrap transition
for the old process, the chosen startup/shutdown effects and fallback limits.
There is no supported all-agent barrier in PID 28093, and this code cannot be
loaded into it by updating files. Do not infer old-process idle from this test.
For a future already-instrumented service, the trusted owner must close admission,
obtain a current settled receipt, and keep admission closed until the authorized
signal. Any blocker/timeout is an abort; no automatic replay, forced termination,
credential/approval refresh, ownership change or merge is permitted.

Source rollback cannot undo durable startup/shutdown writes or recreate transient
state. An operator must separately qualify any required consistent data backup.
The next decision is bounded: retain the current service, or separately authorize
an initial transition once old-process quiescence and the enumerated effects have
been resolved. PR #4 and PR #5 remain draft and unmerged.
