# DISCOVERY-002S acceptance audit

Candidate executable source: `f650268162ce5f3be9704f9c6c9f09941981ee16`.
Startup manifest: `e7d785f25cf1a40c85b8044beb1466f9c9318bda817b08e3c44ccd64ccc0dd22`.
This milestone prepares maintenance. It does not update the live service.

| Requirement | Evidence and result |
| --- | --- |
| Startup hook, inactive by default | Launch helper plus private process-local object; no app flag, environment field, HTTP route or tool registration enables it. Source and ordinary source/desktop startup tests pass. |
| Private, one-use, launch-bound authentication | Canonical path/UID/mode/ancestor/filesystem guard, strict schema, expiry and interpreter/data/source bindings; durable exclusive claim and fsync; recreated request rejected in a fresh process. Three cold negative cases reject without data/log initialization. |
| Normal startup compatibility | Existing default startup order retained without a pending launch object. Pure shared file guard body matches the old implementation exactly. Lazy public exports preserve canonical objects. Focused 386 cases pass; hosted gate below. |
| Disposable end-to-end startup and rollback | [Final process receipt](startup-final-rehearsal.json): candidate PID 16350 and fallback PID 16360 used the same disposable cwd/interpreter/data, returned health 200, exited on SIGTERM with code 0, and retained fictional rows/unrelated sentinels. Actual git restore command matched pinned fallback runtime files. |
| Runtime migration compatibility or explicit block | [Schema/marker evidence](startup-migration-drain.json): global composite schema is current; testpilot2 secondary has no conversation tables. Expected change is one marker, with no conversation import/delete. Fictional migration/retry tests pass. Live write/startup effects remain unapproved; zero-write maintenance is blocked. |
| Live service preserved | PID 28093/start 1794162129.482237 remained on 127.0.0.1:9899. Disposable processes used 19882 and exited; no disposable listener remains. No live stop, model task, profile change, authority refresh or private Agent memory read. |
| Hosted CI on new fingerprint | [Run 42683270955](startup-hosted.json) passes all five jobs on the frozen source: Linux 3.11/3.13 each 6,069 passed/46 skipped; macOS 6,076 passed/39 skipped; each 93 subtests. JS/build/Ruff pass. Exact comparison: 6,115 named cases, 33 added, none removed, unchanged platform skip sets. One targeted macOS retry; four successful executions retained. |
| Independent review | [Source/corrective/packet review](startup-review.md): no actionable findings remain. The concrete packet is conditional and explicitly NO-GO for live execution. |
| Exact interpreter and dependency environment | [Process launcher evidence](startup-launch-fidelity.json) identifies repository .venv Python, verified prefix and installed dependency compatibility. Exact shell spelling and loaded old source are not claimed. Full environment must be privately preserved in memory only during separately approved maintenance. |
| All-agent drain requirements | Source-mapped requirements cover channel admission/turns, all registered agents, scheduler due/callback work, recovery/verification/publication, evolution and external actions. Existing process has no supported aggregate control/receipt. This is a genuine live no-go, not inferred idle from health/counts. |
| Concrete maintenance approval packet | [Packet](startup-maintenance-packet.md) contains real interpreter, candidate/fallback commits, strict request builder, pre-signal validation/lifetime bound, PID checks, graceful stop/launch and in-place rollback commands. [Command check](startup-packet-command-check.json) records syntax and fictional builder/freshness execution. No live controller block was executed. |

## Boundaries retained

The startup observation cannot manufacture a current caller, receiver authority,
proof or capacity. The real disposable observation lists three fictional
registered identities and returns denied selections; it is not live TestPilot
acceptance. Native initialization remains runtime-owned. Private file provenance
and ownership-ignored mount rejection remain unchanged. Source hashes describe
launch files, not universal loaded-code attestation.

The first hosted run on `25890e8c` had three existing runtime-reader initial
selection failures on Linux 3.13. Its [receipt](startup-hosted-initial.json) remains
retained. A deterministic bind-before-listen counterexample justified the fixture
readiness correction; exact original CI causation remains unproven. No test was
removed or assertion weakened. The new run passes the full required matrix. Its
first macOS job was cancelled without a runner or executed step; GitHub supplied
no cause. One targeted retry executed successfully. No cancelled job is counted
as test evidence.

The [earlier rehearsal](startup-rehearsal.json) and [initial fixed-cwd rehearsal](startup-inplace-rehearsal.json)
are historical evidence for their exact fingerprints. Final-source claims use
`startup-final-rehearsal.json`. No valid evidence was relabeled as live integration.

No restart, ownership/remount, credential or task approval refresh, activation or
merge is authorized. PR #4 remains draft. Supported old-process drain and explicit
acceptance of maintenance effects are still required before live execution.
