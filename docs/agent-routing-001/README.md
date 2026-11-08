# AGENT-ROUTING-001: registered TestPilot delegation

**Passed on 2026-11-08.** Codex submitted one fictional read-only analysis over
authenticated private Unix IPC. CowAgent resolved the existing `testpilot`
profile, initialized its native Agent and returned the correct report. The
adapter did not replace the registered prompt, model, memory manager or runtime.
This is an opt-in experiment on `codex/agent-routing-001`, not a production
service activation or a change to generic `agent_delegate`.

## Manual chat trace and registered configuration

The retained native log is
`/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData/run.log`.
Only routing/startup metadata was extracted; no prompt, memory fact, private
conversation or provider secret is published.

- Lines 782–784, 2026-11-06 17:47:24: native startup registered `default` and
  `testpilot` under the current `CowAgent-Runtime/workspace` root.
- Line 814, 17:47:59: `[Routing] → 🤖 TestPilot(testpilot)`, emitted by the native
  manual reply path in `bridge/agent_bridge.py`. Earlier routing events at
  lines 65, 251, 353, 369, 384, 488, 519, 651, 706 and 743 confirm repeated
  named selection. These are retained real chat logs, not a fresh UI replay.

Current source resolves that path as follows:

| Stage | Source | Behavior |
| --- | --- | --- |
| UI selection | `channel/web/static/js/chat/state.js:45`, `send.js:130` | Adds selected `agent_id`; keeps per-agent chat session IDs; posts `/message`. |
| Route | `channel/web/core/channel.py:1017`, `agent/routing.py:51` | Requires an explicit target to exist and be enabled. |
| Manual reply | `bridge/agent_bridge.py:1497` | Resolves owner/speaker and logs the actual registered speaker. |
| Native instance | `bridge/agent_bridge.py:1213` | Caches by `(agent_id, session_id)` and applies session preferences. |
| Native initialization | `bridge/agent_initializer.py:135` | Resolves profile workspace, memory manager, tools, context files and skills. Lines 226–230 apply profile model defaults; session history is restored for that session. |
| Prompt and execution | `agent/protocol/agent.py:316`, `:767` | Uses native dynamic prompt construction and `AgentStreamExecutor`. |
| Manual persistence | `bridge/agent_bridge.py:1703` | Records the chat run and messages separately from model execution. |

Registry metadata was read from the native team roster, not invented by Codex:

| Property | Observed value |
| --- | --- |
| Registered ID / display name | `testpilot` / `TestPilot`, enabled |
| Profile model/provider overrides | Absent; native inheritance applies |
| Effective configured model / provider | `nvidia/nemotron-3.5-super-vl:free` / `custom` |
| Agent workspace | `/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace/agents/testpilot` |
| Memory ownership | Native `MemoryManager` for that workspace; no caller-selected user identity |
| Ordinary session behavior | Profile-scoped runtime cache and restoration of the selected session's native transcript |
| Experiment session | Fresh server-generated `f96a59e3-108e-4b06-9ac8-55cebf1aac79`; native history must initially be empty |

The experiment calls native `get_agent` and `run_stream` directly. It keeps its
task/result in the approval and adapter journals; it does not add a manual UI
chat transcript. It does not reuse or expose an existing private conversation.

## Adapter contract

`cowagent_cli` launches a separate CowAgent process with the existing config.
It does not start the web console or enable its external chat API. The native
process performs startup preflight, resolves the registered target and runs its
normal initializer, prompt builder, memory manager and model adapter.

The client uses unchanged `ExternalTransport`, `ExternalSupervisor`,
`ApprovalJournal`, `OperatorControl` and `AnalysisVerifier`. A strict tagged
enrollment binds `testpilot`, effective provider/model, profile, configuration,
credential-file and executable-source fingerprints. The existing Codex
enrollment format remains supported unchanged. Only `analyze_records` with its
bounded fictional record schema is available. Request fields cannot select a
system prompt, replacement model, private path, transcript or native session.

The native process enters the receiver's `RuntimeIdentity`, resolves a fresh
session, and applies existing `read-only` permission. It leaves generic worker
`authority` unset, so the native prompt builder still loads the registered
instructions and memory normally. Codex attribution is part of the user task.
It sets normal provider routing metadata to the registered agent and new
session. A fallback model/provider cannot silently satisfy this enrollment.

Existing native `agent_delegate` intentionally constructs a generic restricted
child without persistent receiver memory/context. It cannot satisfy this
experiment. Its authority and isolation contracts remain unchanged. This
adapter supplies a separate approved protocol to the persistent native path;
it does not bypass or relabel the old delegated-child route.

Approval admission and native/publication intents use the existing atomic
journal gates. Duplicate requests return the retained task. Restart or ambiguous
execution never replays or republishes. Revocation fences later publication and
requests cooperative cancellation. An uncertain native attempt stays explicit.

Only an exact fixed analysis result can leave the runtime. Schema validation
alone would allow private text in string fields, so equality is checked before
export. A separate verifier then reads the artifact and checks its hash and
calculation. Raw model text, reasoning, tool arguments and private context are
never returned by the endpoint.

## Evidence

- [Focused checks](focused-validation.json): 163 passes, no failures or skips;
  relevant registry/routing, native seam, isolation, enrollment, approval,
  authenticated transport and supervisor cases. Ruff F and staged diff checks
  passed. A final test-file whitespace cleanup preserves the same AST;
  [final validation](final-validation.json) records both hashes without changing
  the original receipt used for enrollment.
- [Native receipt](native-receipt.json): completed and verified; one submit,
  one native and one publication intent. Zero tool events. Duplicate submission
  retained the same session. The unapproved request was rejected before dispatch.
- [Returned fictional report](report.json): 20,000 paid cents, -2,000 refund
  cents, 3,000 pending cents, **18,000 net cents**; four valid records and three
  exceptions. A second arithmetic check does not call the runtime verifier.
- Postflight native snapshot equals preflight: profile, effective config,
  credential-file and source fingerprints match. No context-file creation or
  removal event was observed. The owned native process exited after the probe.
- The caller audit guard was configured to deny opens under the actual native workspace, data
  directory and `~/.cow`; it recorded zero private open attempts. The caller and
  native process are separate. Only CowAgent itself loaded private context.
- One Sol 6.1 security/engineering review found no remaining blocker after
  corrections for MCP fallback config, scheduler backup loading, provider
  fallback attribution, parse-error privacy and provider session metadata.
  Independent Luna verification is recorded in [review.md](review.md).

## Running the bounded experiment

The runner requires a real local config, registered target and passing source
receipt. It creates a private disposable control/IPC directory and an expiring
credential; it does not change the existing model/config or expose a TCP port.

```sh
.venv/bin/python docs/agent-routing-001/run_acceptance.py \
  --config '/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData/config.json' \
  --private-workspace '/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace' \
  --probe-receipt docs/agent-routing-001/focused-validation.json --execute
```

Do not rerun an accepted interaction merely to regenerate evidence. The retained
fixture is `/private/tmp/cowagent-routing-kwzz7xni`. Its launch credential and
raw native logs remain private and are not committed. The service lifetime is
bounded to five minutes, credential expiry and the native maintenance window.

## Limits

Authentication proves a scoped credential held by the trusted local Codex
caller. It is not application signing, human-presence proof or isolation from
hostile same-account code. The Python audit guard is process instrumentation,
not OS confinement. Source review and runtime receipts support this invocation;
they are not a universal proof about all processes on the host.

Read-only describes task tool authority. Native memory/index maintenance and
runtime bookkeeping remain native-owned. This probe does not claim all private
database bytes stayed unchanged. It does show the registered memory scope was
retained and the client did not read private contents. Broader memory-aware tasks
and arbitrary output are deliberately excluded.

Cancellation is cooperative, not proof of all-descendant exit or a hard cost
ceiling. Crash/restart and revocation behavior have focused fixture coverage;
this milestone made one real successful model run, not a new live crash campaign.
No broad regression or UI replay was required: native chat, prompt, permission
and model source is unchanged. No production activation or master merge occurred.
