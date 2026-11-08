# AGENT-ROUTING-003: two persistent named agents

This report records the original milestone source and accepted runs. See the
[integrated merge review](merge-review.md) for later baseline repairs, full
regression results and fresh native acceptance attempts. Historical acceptance
does not attest to a later executable-source fingerprint.

**PASSED on 2026-11-08.** Both registered agents completed one independently
verified task through the authenticated adapter. Native execution windows
overlapped by **13.912 seconds**. Distinct profile, memory-scope, session, run and
process bindings were verified. The existing webserver stayed on PID `28093`.

This milestone extends the authenticated persistent-agent adapter to registered
`testpilot` and `testpilot2`. Each native process resolves its own profile through
CowAgent's registry and uses normal `get_agent` / `run_stream` initialization.
Registered instructions, skills, model inheritance and native memory ownership
remain in CowAgent. Native `agent_delegate` is unchanged.

The implementation uses one target per authenticated endpoint. It adds no new
registry, orchestrator or public API. The existing webserver is separate from
the bounded Unix-socket runtime processes used for acceptance.

## Fixture failures resolved first

The old parallel-tool fixtures passed `agent=None` to `AgentStreamExecutor` and
used custom tool classes without registered permission descriptors. The real
permission gateway rejected those calls before their test bodies ran.

The correction supplies a minimal read-only Agent context and uses the registered
parallel-safe `SubagentTool`. Each test replaces only the tool's execution body.
Authorization is not mocked, disabled or made permissive. The ordinary-tool case
uses the registered `TimeTool` and still proves that it is not scheduled in the
parallel group.

Before the correction, the test file had four failures and two passes. After it,
the four affected cases passed, the whole file passed 6/6, and the broader
delegation/isolation/recovery selection passed 60/60. The adapter implementation
started only after this gate passed. [fixture-checks.json](fixture-checks.json)
records the diagnosis and results.

## Authentication and selection

- Inspection accepts `--agent-id testpilot` or `--agent-id testpilot2`. Serving
  derives the target only from the approved enrollment. Unknown or disabled
  registry targets fail before native execution.
- A credential's runtime ID must be `cowagent.<registered-agent-id>`. The task
  specification and authenticated envelope must match that runtime. Task text
  cannot select another agent, model, memory path or existing session.
- Each target has a separate enrollment, credential/key, operator scope, Unix
  socket, runtime journal and export directory. Profile/config/source hashes and
  effective model/provider are bound to enrollment. Current approval is checked
  again at native admission and publication.
- Native prepare obtains a fresh server-owned session under the receiver's
  runtime identity, with native read-only permission. It does not replace the
  system prompt or attach generic worker authority. The registered memory manager
  stays attached. Existing chat history is not borrowed.
- Results must equal the exact fixed fictional analysis contract before export.
  A model's self-name is not execution evidence. Published native metadata binds
  registered ID/name, profile hash, model/provider, memory scope, session, run,
  process, timing and permission to the prepared native instance.

## Memory ownership and concurrency

Before Bridge initialization, supported target workspaces must not overlap.
Each memory-index path must resolve inside its own canonical workspace. Existing
databases must have different device/inode pairs. This rejects directory/file
symlinks and hard links that would merge the two memory scopes before a native
memory manager opens either database.

After initialization, the actual memory manager's workspace, configured index
path and opened storage path must match the registered target. Receipts expose
only a digest of the workspace/index path pair. They do not contain memory text,
private prompts or raw paths. The profile hash separately binds that scope to
the registered agent.

Each adapter runtime serializes its prepare/run/close sequence with a dedicated
lock. Status and cancellation keep their own mutex and remain responsive.
Queued cancellation and expired approval are checked before native admission.
Distinct target processes can overlap without sharing an Agent, model object or
module-level configuration. This is not a guarantee of parallel execution at
the remote model provider or a speedup guarantee.

Recovery preflight now permits settled historical rows. It still rejects queued
or running tasks and completed tasks that lack a verification record for the
current attempt, matching the native recovery consumer. It does not reset,
delete or modify existing recovery state. Uncertain adapter execution remains
non-replayable; completed duplicates return the retained session/result.

## Verification

[focused-validation.json](focused-validation.json) records 202 passing focused
regression tests. After the review's database-alias correction, all 22 native
entry-point tests passed, including three new pre-initialization alias cases.
The earlier 202-test receipt retains its source hashes; the final native check
and final source hashes are recorded separately. No full-suite claim is made.
A final fixture-only change uses `Path.home` patching instead of changing the
HOME environment; its five recovery cases passed. The separate
[follow-up receipt](fixture-final-check.json) leaves the enrolled probe receipt
unchanged. Application source and the accepted live evidence are unchanged.

Tests cover both targets with different fixture models, target/enrollment and
credential mismatch, invalid receipt fencing, memory-scope mismatch, same-runtime
serialization and queued cancellation, separate-runtime overlap, settled versus
pending recovery, and the existing approval/revocation/no-replay behavior.

One independent Sol 6.1 review examined authentication, private-memory ownership,
concurrency and evidence handling. It found two concrete issues before live
execution: resolved database aliases could pass the initial check, and postflight
preservation failure did not prevent a successful acceptance flag. Both were
corrected. The review did not launch models or inspect private runtime data.

[tasks.json](tasks.json) contains two five-row fictional datasets and fixed
expectations. A has three accepted rows and net **17,400 cents**; B has three
accepted rows and net **20,000 cents**. Both have two exclusions. Expectations
remain in the caller verifier; native tasks receive only their own records and
the normal analysis rules/schema.

The [acceptance client](run_acceptance.py) uses the existing transport, supervisor,
operator journal and analysis verifier. It checks signed target-override and
cross-runtime task rejection, submits the two approved tasks once, verifies
artifacts and native bindings independently, and counts durable intents. Wrong
credentials receive no authenticated response; this observation alone is not
treated as proof of rejection. Accepted work is not replayed to repair evidence.

The caller has a Python-open audit guard for the native data directory,
workspace and `~/.cow`. Only the native processes inspect private state. The
client's final acceptance flag also requires matching native pre/post snapshots,
zero guarded private opens and exit of its owned processes. Raw launch secrets
and native logs remain in the private fixture directory and are not published.

## Live result and durable evidence

The [native receipt](native-receipt.json) retains both actual reports and their
artifact hashes, authenticated discovery, native bindings, intent counts,
pre/post snapshots and independent verification outcomes. It contains no launch
credential, private prompt or raw model log.

| Property | TestPilot | TestPilot2 |
| --- | --- | --- |
| Registered ID | `testpilot` | `testpilot2` |
| Runtime ID | `cowagent.testpilot` | `cowagent.testpilot2` |
| Task | `c2613519-d79d-4d8b-bb68-db7041931507` | `64299e66-5053-4560-898a-b9e5150e89b6` |
| Native session | `37484f4d-0a39-461e-a226-a1820bbd34a5` | `cd6b289b-5ce8-40ac-ad35-c042966dfb84` |
| Native run | `9df4f8dac5f84019b57a7bb56993731f` | `a5b8a34617c443be96c66d0377462ecc` |
| Native process | `33418`, exited | `33422`, exited |
| Local execution, EST | 14:07:28.581–14:09:25.662 | 14:07:28.581–14:07:42.493 |
| Configured model/provider | `nvidia/nemotron-3.5-super-vl:free` / `custom` | Same inherited configuration |
| Accepted rows / net cents | 3 / **17,400** | 3 / **20,000** |
| Native tool events | 0 | 0 |
| Submit/native/publication intents | 1 / 1 / 1 | 1 / 1 / 1 |
| Independent verification | Passed | Passed |

The native processes had different profile and memory-scope digests. Each scope
matched its inspection metadata and the actual checked native manager paths.
Both runs preserved native prompt/memory ownership and read-only permission.
Zero caller guarded-private-open attempts were recorded. A separate reviewer
recomputed both calculations, dataset/artifact hashes, all identity bindings,
intent counts and overlap without reading private state. See [review.md](review.md).

Both native snapshots matched after execution: enrolled profile/config/source,
model/provider and known context-file metadata. The private fixture remains at
`/private/tmp/cowagent-routing003-ll5hc8if`; durable operator/runtime journals and
exports are retained there. Normal native index/bookkeeping writes are not
claimed absent. The adapter's fresh sessions are recorded in its journals, not
as manual chat transcripts. Both owned native processes exited; the existing
`127.0.0.1:9899` listener remained PID 28093.

Reproduction requires the registered targets and a fresh passing source receipt:

```sh
.venv/bin/python docs/agent-routing-003/run_acceptance.py \
  --config '/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData/config.json' \
  --private-workspace '/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace' \
  --probe-receipt docs/agent-routing-003/focused-validation.json --execute
```

This command makes new model calls. Do not rerun the accepted pair for
bookkeeping. Use the retained receipt and journals for further review.

## Operating limits

This is a bounded trusted-host experiment. Native profile memory and skills
remain available to the receiver; native read-only task permission does not
prohibit its normal index or bookkeeping writes. A fresh adapter session is not
a resumed manual chat transcript. Normal native shared knowledge fallback, when
configured, is separate from ownership of each private memory database.

Path checks do not lock the filesystem against a trusted same-account actor
changing symlinks after preflight. Python-open instrumentation is not OS
confinement. Model/provider evidence is local native configuration and execution
metadata, not remote provider attestation. Cancellation is cooperative, with no
hard cost or all-descendant termination guarantee. Same-target serialization
applies within an adapter runtime, not every manual session or separately
launched process on the host.

This milestone does not enable arbitrary targets or outputs, change production
profiles, merge master, install a persistent service, or deploy the adapter.
