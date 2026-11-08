# EXTERNAL-002: Codex runtime investigation and blocked adapter gate

Historical assessment at `26c8e77d`. The later
[EXTERNAL-002B supervisory integration](../external-002b/README.md) supersedes
this deployment decision for its explicitly enrolled analysis/artifact operation.
The original evidence and limitations below remain recorded.

**Deployment decision: BLOCKED — do not enable live orchestration or merge this
branch into master.** The required real adapter is not complete. This branch
contains the integrated EXTERNAL-001 dependency, an unregistered transport and
configuration foundation, tests, and evidence for the blocked security gate.

The installed Codex/provider combination advertises `collaboration.spawn_agent`
and `collaboration.followup_task` to the model while both Codex multi-agent
feature flags report `false`. Their enforcement and effect lifetime were not
established. No collaboration operation was invoked to test that boundary and
no escape was demonstrated. Changing the model, provider, authentication or
permissions to bypass the gate was not attempted.

## Integration and scope

- Baseline: fork `master` at `e642eec11c4fba1b193d49c7dadb3d02d4667ce0`.
- Dependency: published `feat/external-001-runtime-contract` at
  `bfd64e39feaa198da80c301da507949c5617c329`, whose parent is the baseline.
- Development branch: `feat/external-002-codex-adapter`, fast-forwarded to that
  dependency before new work. Master is unchanged.
- The published EXTERNAL-001 README blob was checked against the local Git
  blob: `3a11f1d3a0734789aab93e89f086b7d7c08fbb03`. Its
  [report and full evidence](../external-001/README.md) remain unchanged.
- No production CowAgent memory, configuration, model selection, agent identity
  or instruction files were modified. No supervisor endpoint was exposed over
  a network. New modules are not imported by a tool, route or live supervisor.

## Installed runtime and supported interface

Observed on macOS/arm64 with Codex CLI **0.165.0**, invoked through
`/opt/homebrew/bin/codex`. `codex login status` reported ChatGPT authentication.
The existing selection was `gpt-6-astra`, provider `codex-pooler-ws`, reasoning
effort `ultra`. These values were omitted from task invocation overrides and
returned unchanged by native thread creation. The installed model catalog
reports Code Mode as this model's tool mode.

| Interface | Observed capability | Decision |
| --- | --- | --- |
| `codex exec --json` | Scripted input, JSONL events and native resume | Smallest general scripted entry point; not selected for this contract |
| `codex app-server --stdio` | Public request/notification protocol, named thread permission profiles, interrupt and persisted history reads | Selected candidate; private owned pipes only |
| `generate-json-schema --experimental` | Installed-version schemas for the public app-server API | Used to check exact request/response fields |
| `codex sandbox -P <profile> --include-managed-config -- <fixed command>` | Native permission-profile probe | Used only for fixed fictional canaries |

The documented scripted CLI does not establish that stopping its main process
terminates every possible descendant. The selected app-server interface also
provides explicit per-thread profile selection, which matters when the existing
configuration contains legacy sandbox settings. Both profile support and the
app-server API require version-specific validation. See the official
[developer commands](https://learn.chatgpt.com/docs/developer-commands#codex-exec),
[app-server protocol](https://learn.chatgpt.com/docs/app-server), and
[permissions documentation](https://learn.chatgpt.com/docs/permissions).

No internal session database or undocumented API is used. `process/spawn`,
`thread/shellCommand`, arbitrary command RPCs, configuration writes, auth changes
and automatic native session resume are excluded from the transport allowlist.

## Foundation delivered

[`codex_client.py`](../../agent/external/codex_client.py) implements one owned
stdio process, bounded JSON frames and writes, correlated concurrent requests,
notifications, explicit timeout/EOF errors, and no automatic retry. Escalation
requests are declined; unknown server requests are rejected. Closing the client
cleans its process group even when the leader has already exited. This is not
a guarantee about descendants that detach from that group.

[`codex_policy.py`](../../agent/external/codex_policy.py) is a candidate
configuration checker pinned to CLI 0.165.0 on macOS. It selects a named
permission profile, requests that model shell and alternate service surfaces be
disabled, removes inherited shell values, disables configured MCP servers, and checks the
effective model, profile and configuration metadata. It never reads credential
files. The selected provider's existing environment credential, if configured
and already present, can pass directly to Codex; it is not stored in arguments,
journals, reports or prompts. All credential test fixtures are fictional.

`attest_configuration()` deliberately certifies settings only. It does not
certify the actual tool boundary or approve execution. These helpers are not
an EXTERNAL-001 adapter implementation or an exposed command facility.

The default candidate disables the native Code Mode host. A separate inventory
probe retained that documented host, with shell and all other exclusions still
disabled, because the selected model did not edit through the first candidate.
That inventory revealed the blocking capability advertisement. See the official
[native Code Mode host interface](https://learn.chatgpt.com/docs/app-server#connect-a-remote-code-mode-host).

## Protocol mapping and unfinished contract

This mapping describes supported primitives and the remaining adapter work;
it does not claim the complete contract is implemented.

| Required operation | Public Codex primitive | Current evidence / missing work |
| --- | --- | --- |
| Capability discovery | `initialize`, `permissionProfile/list`, `config/read`, `experimentalFeature/list`, `mcpServerStatus/list`; raw response items | Configuration and actual advertisement inspected; capability gate blocked |
| Submission | `thread/start`, `turn/start` | Native probes ran; no versioned EXTERNAL-001 adapter registration |
| Durable identity and idempotency | Native thread/session/turn identifiers | References observed; durable supervisor binding and duplicate suppression not implemented |
| Status and progress | Native item and turn notifications | Structured notifications captured; durable progress mapping not implemented |
| Cancellation | `turn/interrupt`, followed by native completion evidence | Public schema inspected; cancellation during actual execution not tested |
| Confirmed termination | Owned process cleanup plus effect-quiescence evidence | Fake-process cleanup tests pass; detached or alternate worker effects unproven |
| Result retrieval | Completion notifications and `thread/items/list` | Completed native history read through a new app-server process |
| Independent verification | CowAgent native read-only artifact checks | Actual fixture bytes checked; requested edit failed; behavioral tests not run |
| Restart reconciliation | Read persisted native references without resume | Read-only primitive proved; active adapter restart, uncertain send and no-replay mapping not implemented |

EXTERNAL-001 already tests its synthetic contract's durable send intent,
idempotency, approval, reconciliation and cancellation. Those results do not
prove the equivalent behavior of Codex. An eventual adapter must persist intent
before submission, never replay an uncertain send, and keep transport loss
separate from confirmed task termination.

## Actual runtime evidence

The sanitized structured receipt is [runtime-gates.json](runtime-gates.json).
It includes native identifiers, correlated call/output records, exact public
metadata and source-receipt hashes. Raw transcripts are not published: they
contain instruction, account/context and reasoning material unrelated to the
acceptance evidence. Agent final explanations are not acceptance evidence.

1. **Permission-profile preflight passed.** Native thread creation reported the
   selected profile, `on-request` approval with user review, workspace writes,
   network disabled, both temporary-root exclusions, and unchanged model
   selection. Listed MCP metadata alone was not treated as enabled tools:
   all 13 configured servers later reported disabled with zero tools/resources.
2. **Command sandbox canaries exposed an initial gap.** A profile without
   explicit temporary-root denial allowed reads/writes to fictional outside
   files under `/tmp`. The documented root/minimal/temp-denial profile allowed
   workspace read/write and denied outside reads/writes and symlink reads.
   This proves only that fixed native command probe, not native patch
   confinement, network isolation or unrestricted runtime isolation.
3. **The real edit did not pass.** Native execution completed, but the fixture
   remained `return a - b` instead of the frozen required `return a + b`.
   No native file-change event was observed. Acceptance and independent desired
   state both failed. The selected model's native Code Mode route was disabled
   in that attempt. The trusted-source hash gate never passed, so no behavioral
   test of the model output was executed.
4. **Actual Code Mode inventory was captured.** With the documented native host
   retained, one pure inventory expression returned `process`, `require` and
   `fetch` as undefined and five nested tool names: `apply_patch`, clock, and
   three MCP resource-discovery/read helpers. No nested tool was called. This
   result alone is not a hard-isolation proof.
5. **The top-level advertisement blocked the candidate.** A native
   `rawResponseItem/completed` event of type `additional_tools` advertised the
   separate `collaboration` namespace, including spawn and follow-up mutations.
   Both multi-agent flags had reported false. Ordinary UI item notifications
   omitted the pure Code Mode invocation and result; raw structured call/output
   correlation was needed to inspect the actual surface. The origin of the
   additional advertisement—CLI, provider or another runtime layer—was not
   established. This finding is limited to the tested combination.
6. **Completed native history survived a process restart.** A fresh app-server
   read the owned completed thread with `thread/items/list`. This is evidence
   for the history primitive, not for a durable CowAgent task or active recovery.

All real work used an owned disposable Git repository with fictional arithmetic
code and canary files. It had no remote. Model shell, production repository
access and credential probes were not enabled. Native patch outside-root and
protected-file canaries, real cancellation, duplicates and uncertain replay
tests stopped at the blocked gate. Thus absence of unauthorized access is not
certified for an eventual real adapter.

Codex itself added a trusted-project entry for the disposable repository during
thread creation. After the probes, only that exact new entry was removed.
The candidate restoration was required to hash to the original file before
writing, and concurrent change was checked. The final config SHA-256 equals
the initial SHA-256:
`7d926393273708a5069849a4ea37e94c53fbfbfb7271c6a1cdbe2ffb742874cc`.
No model, auth or provider setting was changed. Native test history remains
owned by Codex; no native history or production database was deleted.

## Regression and review results

Fresh applicable regressions cover the integrated SQLite fix, efficiency
Phases 1–4, isolation, recovery, verification, renderer correction, EXTERNAL-001
and the new foundation tests. Passing these gates does not close the real
adapter security gate.

| Gate | Result |
| --- | --- |
| `.venv/bin/python docs/external-002/run_regression.py` | 1,405 passed, 15 skipped; 124 files, 1,420 JUnit IDs |
| Seven exact browser skips, rerun in private HOME/data | 7 passed; deduplicated total **1,412 passed, 8 Windows-only skips** |
| New Codex foundation tests | 17 passed, included above; fake processes/configuration only |
| EXTERNAL-001 contract/process tests | All 24 passed, included above |
| Node usage/scroll/message tests | 39 passed |
| Strict renderer `tsc --noEmit -p tsconfig.json` | Passed; strictness unchanged, former nine errors remain fixed |
| Desktop `npm run build` | Passed with existing non-fatal warnings |
| Ruff F and in-memory compilation | Passed for five new Python files; retained static evidence reused after all 66 source hashes matched |
| Independent security and architecture review | Capability blocker confirmed; one process-group cleanup defect fixed and narrowly rechecked |
| Complete real-adapter acceptance | **BLOCKED / not passed** |

Evidence: [regression.json](regression.json), [JUnit](regression-junit.xml),
[command output](regression-output.txt), [UI/browser gates](ui-gates.json), and
[independent review](review.md). The runner directly reuses the retained private
regression harness and adds the two Codex suites. Its `real_codex_calls: 0`
applies to the offline regression run, not the separately documented probes.

## Limits and next gate

This is trusted host code, not a hard-isolation boundary. The beta runtime is
version-pinned; other versions, Linux and Windows are unverified. The transport
has an unbounded event queue and does not certify detached descendant shutdown.
Native authentication and model requests require Codex's own network access;
the sandbox profile is not an assertion that the entire runtime has no network.
No human approval service, durable Codex adapter, live registry entry, real
idempotency or active restart/cancellation contract was delivered.

Resume only after a supported control or authoritative matching-runtime
implementation establishes that all excluded worker mutations are unavailable
under the enrolled policy. A prompt instruction or an unchanged feature flag
is insufficient. Then repeat actual capability discovery, prove native patch
and symlink/protected-file restrictions, and implement the durable mapping.
Run every remaining real acceptance case, repeat the applicable release gates
and obtain review before considering merge or activation. Keep the existing
Codex authentication and model selection throughout.
