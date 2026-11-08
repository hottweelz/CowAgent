# AGENT-ROUTING-002: live native multi-agent delegation

**Assessment: PARTIAL — 2026-11-08.** The existing CowAgent supervisor made two
real native `agent_delegate` calls to registered `testpilot` and `testpilot2`.
Both completed once, in sequence, and returned correct calculations. Native
routing and recovery records identify the correct targets. Both returned
`"agent_id": "CowAgent"`, however, and neither loaded the persistent target's
instructions, memory manager, skills or conversation history. Ordinary native
delegation is therefore not equivalent to the persistent named-agent path in
[AGENT-ROUTING-001](../agent-routing-001/README.md).

This task changed audit files and project continuity notes only. It did not
change application code, profiles, permissions, model configuration or native
delegation behavior. The existing server stayed running; no second server,
restart, deployment or master merge was performed.

## Runtime and registry preflight

The audit branch is `codex/agent-routing-002`, based on the current repository
state `90c3cd8f72ffe7a47cb20925fa538eda479317c6` (AGENT-ROUTING-001).
The earlier master baseline is `9cd8c535`. Starting from the current state kept
the reference adapter available without merging it into master.

| Item | Observed value |
| --- | --- |
| Existing listener | PID `28093`, Python 3.13, `127.0.0.1:9899`; started 13:22:09 EST |
| Source directory | `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent` |
| Configuration directory | `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData` |
| Active workspace | `/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace` |
| Registry | `default` / CowAgent, `testpilot` / TestPilot, `testpilot2` / TestPilot2; all enabled |
| Profile model/provider overrides | Absent for all three; native global inheritance applies |
| Effective configured model/provider | `nvidia/nemotron-3.5-super-vl:free` / `custom`; fallback disabled |
| Current permission | `workspace-write`; unchanged throughout the audit |
| Delegation policy | Enabled; no additional target ACL; max depth 3, timeout 600 s, max task length 8,000 characters |
| Other runtime settings | Self-evolution and external chat API disabled; existing loopback console required no password |

Process/cwd/open-file metadata, the live registry/settings endpoints and
[preflight.json](preflight.json) establish this state. The targets have separate
workspace paths under `workspace/agents/testpilot` and `workspace/agents/testpilot2`.
Session roster membership is also required by the native tool. The audit added
both targets to one new default-owned session before its first message; it sent
no model or permission setting.

The retained manual TestPilot2 chat is separately corroborated by the native
13:25:32 EST routing log, a memory-manager initialization message, and a completed
two-message persistent session. Its session is
`session_aca53dd1-ce30-4207-b4c5-31d5c3ccc3df`; run
`52ea1037f6cd4cd898e200ab093497f8` completed at 13:25:34. Only metadata was read.
The process also had that target's private memory index open. These observations
show persistent manual behavior, not persistent context in a delegated child.
[postflight.json](postflight.json) retains the sanitized metadata. Historical
TestPilot routing is documented in AGENT-ROUTING-001.

## Actual native path

| Stage | Source and behavior |
| --- | --- |
| Console invocation | `channel/web/core/channel.py`: `/message` with both owner and speaker explicitly `default`; `/stream` observes the returned request ID. Session settings supply the native roster. |
| Supervisor | `bridge/agent_bridge.py:1497` resolves the registered speaker; `get_agent` at line 1213 obtains its native instance. `bridge/agent_initializer.py:993` registers delegation for eligible sessions. |
| Admission | `agent/tools/agent_delegate/agent_delegate.py:426`: resolves source/target, checks enabled state, roster/ACL, cycle/depth and message limits. |
| Child construction | Same file, lines 545–600: derives receiver authority and intersects caller authority; creates a **fresh** Agent with the target profile's model defaults. It does not call persistent receiver `get_agent`. |
| Context | Generic delegated-worker system prompt; `memory_manager=None`, skills disabled, `skip_context_files=True`. `agent/protocol/agent.py:316` uses the restricted prompt path. |
| Native execution | `snapshot_child` records the frozen spec; `identity_scope` at delegate line 646 selects target identity/session; `agent/recovery/runtime.py:384` executes the task with cleared history. |
| Completion | Native task/attempt journal, peer events and tool result complete; `_open_run` in `agent/subagent/runner.py:205` creates display rows owned by the source session. |

The native runtime, model adapter, identity scope, locks and recovery machinery
were used unchanged. Codex sent the supervisor a fictional task request. It did
not execute worker logic itself or replace a persistent target profile.

## Fixed fictional tasks

[tasks.json](tasks.json) freezes the input and expected results. Amounts are integer
cents. First occurrence of each ID wins; later occurrences are `duplicate_id`.
Void rows are `excluded_status`. Paid amounts must be non-negative and refunds
non-positive; wrong signs are `invalid_sign`. Exclusion indices are zero-based.
Accepted rows are valid paid/refund rows. Refund totals keep their negative sign.

| Task / target | Five input rows, in order | Expected result |
| --- | --- | --- |
| A / `testpilot` / `AGENT-ROUTING-002-A` | A1 paid 12,500; A2 paid 7,300; A3 refund −2,400; A4 void 500; A5 refund 900 | 3 accepted; paid 19,800; refunds −2,400; **net 17,400**. Exclude index 3/A4/status and index 4/A5/sign. |
| B / `testpilot2` / `AGENT-ROUTING-002-B` | B1 paid 6,000; B2 paid 15,450; B3 refund −1,450; B4 paid −700; B2 refund −500 | 3 accepted; paid 21,450; refunds −1,450; **net 20,000**. Exclude index 3/B4/sign and index 4/B2/duplicate. |

Each worker was asked for JSON fields `agent_id`, `task_id`, `accepted_count`,
`paid_cents`, `refund_cents`, `net_cents`, and `excluded` entries with index/ID/reason.
The supervisor received only input rows, rules and output requirements, **not the
expected totals**. It was instructed to call native delegation twice, give each
worker only its own dataset, and avoid files, memory, history, shell, browser,
network, external actions and additional workers. Native reasoning was not
replaced or replayed. The model chose the observed call sequence.

## Observed execution and independent verification

One new supervisor session:
`audit-routing-002-688ad1f790384d589c86c02672885352`.
One HTTP request: `b05974a6-c3fd-438f-915d-4be7b99d17ee`.
Supervisor run: `2cc37b263395419cb438d4ac2285601a`, completed normally.

| Evidence | Task A | Task B |
| --- | --- | --- |
| Native target ID | `testpilot` | `testpilot2` |
| Durable task ID | `5d027a42-3314-4424-8ea4-be99c00f5e22` | `998f52a9-f68d-49ea-a182-2c880f04c4bf` |
| Attempt ID | `23cf43b6-89f2-4c85-975e-a3d9f8ab616d` | `eb052969-4965-48b6-afb7-90552a960955` |
| Native target session | `delegate_default_testpilot_29160d791426393c` | `delegate_default_testpilot2_29160d791426393c` |
| Attempt interval, UTC | 18:35:28.199–18:35:36.584 | 18:35:36.616–18:35:46.001 |
| Completion | Completed, one attempt, generation 0 | Completed, one attempt, generation 0 |
| JSON identity claim | `CowAgent` — does not match target | `CowAgent` — does not match target |
| Arithmetic and exclusions | All correct; net 17,400 cents | All correct; net 20,000 cents |

Execution was **sequential**. B started 32 ms after A ended. The live SSE also
shows A's tool end at sequence 29 before B's start at sequence 30. There is no
evidence of concurrent execution. `AgentDelegateTool` inherits the default
non-parallel tool flag; the stream executor runs ordinary calls in order.

[live-events.json](live-events.json) records the two real tool calls and target
peer events. [native-results.json](native-results.json) records actual safe JSON
outputs, result hashes, frozen model/authority metadata and attempt windows.
[reconciliation.json](reconciliation.json) requires exactly two unique target
tasks and attempts, correct task identifiers, completed event chains and matching
time windows. The retained SSE projection lacks durable task IDs, so this is a
correlation by isolated parent session, unique target/identifier and time, not a
shared-key join. Display run rows are attributed to `default`; they alone do not
prove target identity. Native recovery target fields and peer events supply that
evidence. The worker's self-description is not used as identity proof.

An independent Luna reviewer recomputed both datasets and checked routing,
source hashes, collector scope and these conclusions. See [review.md](review.md).
Both full JSON comparisons fail solely on the identity claim. This preserves the
actual result instead of relabeling it to make the experiment pass.
Offline reconciliation recalculates both identity and result-match flags. Raw
summary hashes are provenance markers; their input text is withheld, so those
hashes cannot be independently recomputed from the sanitized receipt.

## Model, memory, permissions and durable writes

Both frozen native specs select `custom` and
`nvidia/nemotron-3.5-super-vl:free`, consistent with live settings and registry
inheritance. This proves local configured routing, not remote provider attestation.
No fallback was configured. The native delegate result does not provide a separate
post-run provider attestation; source review and frozen configuration are the
available model evidence.

Both specs identify the generic worker prompt. Source excludes persistent
receiver instructions, skills, memory manager and prior transcript. Deterministic
delegate session IDs identify restricted task execution; they do not turn the
child into the cached persistent receiver. No receiver conversation/session/run
rows were created for these delegate sessions. The default supervisor itself
uses its normal native context; this finding concerns the delegated children.

The native log records two **allowed** `agent_delegate` authorization decisions
for the default run in unchanged `workspace-write` mode. Child authority is
restricted and intersects caller/receiver grants. The allowed tool classes are
Read, Write, Edit, Ls, SearchFiles and TimeTool. This is an allowance list, not a
call receipt. Shell, browser, network, MCP and memory tools are absent. Although
the authority includes delegated capabilities, the child's tool list has no
delegation or subagent tool.

The retained stream contains no worker tool-call events, and both workers have
zero recovery effect rows.
No cross-agent private-memory access was observed. Source and retained authority
exclude both agents' private paths; in this nested workspace layout an excluded
ancestor also covers the target root. No live file-denial probe was attempted.
The audit used metadata and scoped journal results, not private memory bodies or
old conversation contents. These observations and source checks are not an OS
audit or protection against hostile same-account code.

The live invocation created one default session/roster preference, four message
rows, three display run rows, two recovery tasks, two attempts and two native
verification records. The four messages comprise two assistant rows and two user
role rows; one user-role row carries the tool-result envelope, not a second
submitted human request. Receiver conversation rows and recovery effects are
zero. Native verification reports remain unverified without caller check
contracts; the independent arithmetic here is a separate audit result. These
counts identify audit-owned records, not every index/log maintenance write.
**The live databases are not claimed unchanged.**

Postflight retained the same listener PID, config/registry hashes and nine native
source hashes. Known core-file size/mtime metadata did not change. This is not
a byte-for-byte private memory or recursive skills inventory. No database reset,
WAL/SHM rename, profile overwrite or maintenance operation was performed by the
audit. Existing untracked AGENTS.md and four conflicted PID files were preserved.

## Comparison and BullGod recommendation

| Property | Direct manual chat | Native `agent_delegate` in this audit | AGENT-ROUTING-001 adapter |
| --- | --- | --- | --- |
| Identity | Registered persistent Agent | Registered target routing; fresh generic child; wrong self-ID observed | Registered persistent TestPilot resolved by native `get_agent` |
| Instructions/skills | Native profile context | Excluded | Native profile context retained |
| Memory ownership | Receiver's native manager | No manager or private history | Receiver's native manager; caller cannot select private paths |
| Sessions | Selected persistent chat restored | Derived task session; fresh history; source-owned display/journal | Fresh server-owned native session; adapter journal, no manual chat transcript |
| Runtime/model | Native profile inheritance/session settings | Native runtime; receiver profile defaults | Native runtime/model with enrollment and fallback checks |
| Authority | Existing chat permissions | Caller/receiver intersection and native permission gate | Authenticated private IPC, atomic operator approval and native read-only permission |
| Results | Normal chat output | Worker output forwarded; independent checks must be supplied | Fixed fictional analysis only; exact safe-output gate and independent verifier |
| Recovery | Normal chat/run handling | Durable attempts, frozen input, locks, effect fencing; completed work never replays | Durable admission/native/publication intents; uncertain work never auto-replays |

**Support both as distinct execution mechanisms.** Use native `agent_delegate`
for bounded isolated tasks where the target profile's model is useful and
persistent persona/memory is not required. Use the AGENT-ROUTING-001 authenticated
adapter for persistent named-agent context. Do not label native delegation as a
persistent-agent invocation merely because it has the same target ID.

The current adapter enrolls only `testpilot` and fixed `analyze_records` tasks.
TestPilot2 support, broader memory-aware work or service activation requires a
separate scoped enrollment and validation task. This audit implements none of
those changes and does not replace native delegation's isolation contract.

## Checks, reproduction and limits

[focused-checks.json](focused-checks.json) records **55 passing tests** covering
delegation, authority, recovery and ordinary sequential tool execution, with an
isolated temporary `COW_DATA_DIR`. An earlier expanded selection had **56 passes
and 4 failures** in parallel-safe tool fixtures. Their executor uses `agent=None`,
so the permission gate rejects execution with `evaluation_failed` before the
fixture tool runs. These failures are retained and were not fixed in this audit.
They do not demonstrate a native delegation failure; they also prevent claiming
that the expanded selection passed. No full regression was run.

[probe.py](probe.py) is a small client for the existing console. It saves a submit
intent before POST, then observes the same request ID/cursor. It never starts a
server or retries an uncertain submission. It omits full prompts, model reasoning
and private text from retained events. The published fixture contains only the
fictional input; expected totals are excluded from the live model request.

[collect.py](collect.py) opens SQLite with `mode=ro` and `query_only`, queries only
the audit owner/session/task IDs, and exports explicit metadata plus exact safe
fictional calculation fields. Conversation tables are global in the default
index and namespaced by agent ID; receiver memory indexes are not separate chat
stores. The first collector attempt incorrectly assumed otherwise, stopped on a
missing `sessions` table, and was corrected from source. It performed no database
write or model replay.

Reconcile the retained evidence without contacting the live service:

```sh
.venv/bin/python docs/agent-routing-002/collect.py --offline
.venv/bin/ruff check --select F docs/agent-routing-002/probe.py docs/agent-routing-002/collect.py
```

Static checks and evidence parsing are recorded in [static-checks.json](static-checks.json).
Do not resubmit accepted tasks merely to regenerate receipts. A fresh live probe
is a new model invocation and must use a new audit session/state file after a
new runtime preflight. No live crash/restart or cancellation campaign was run;
focused tests cover those recovery paths. Local source hashes and runtime events
are evidence for this experiment, not a fingerprint of every module already
loaded in the server process or an attestation from the model provider.
