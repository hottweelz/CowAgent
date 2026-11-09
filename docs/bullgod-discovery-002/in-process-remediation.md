# BULLGOD-DISCOVERY-002R — trusted in-process integration

## Decision published before implementation

Published as `cf4956dfd359c0e6fdbc97583586a88c1ca54efa` before production edits.
2026-11-09. Continue draft PR #4 on `codex/bullgod-discovery-002`.
The maintainer authorized design, implementation and controlled read-only tests.
No merge, production activation, service restart, host permission or mount change
is authorized. This decision supersedes the earlier hold only for the 002R scope.

**Implement a server-only bridge to the actual initialized runtime. Keep private
filesystem provenance checks unchanged. Live acceptance remains pending and may
remain BLOCKED.** A passing source test is not evidence from the existing service.

### Baseline

The pre-implementation head is `be33256b18e2234acf97323732e6af5a1ee64f9f`;
master and origin/master are `f659349785acf98905901a5cc53921436a109dbc`.
PR #4 is open, draft and unmerged. The feature branch is synchronized, with no
tracked edits. Git fsck succeeds with the same 40 dangling objects; none are
removed. Seven original untracked files, two recovery refs, five conflict-ref
artifacts, their manifest and the clean detached worktree remain intact.

The [fresh baseline receipt](in-process-baseline.json) records process PID 28093,
health 200/ok, unchanged config/profile fingerprints, public route declarations,
and aggregate conversation/operator/recovery counts. Public HTTP declarations
and offline file hashes are baseline observations, not privileged native proof.
Recovery contains two completed tasks and attempts, with zero effects. pCloud's
normal Settings UI shows six Backup entries (one unrelated active, five inactive)
and no Sync entries. No active root overlaps the checkout, Git directory, data
or runtime workspaces. The Settings window was returned to its prior closed state.

### Old blocker and distinct trust domains

The strict file reader rejects the current APFS volume because native
`statfs64`/`fstatfs64` reports ignored ownership. Mode 0755 does not establish
owner-based provenance. The following sources remain distinct:

| Source | Permitted evidence |
| --- | --- |
| Actual initialized server-owned objects | Native identities, current enabled state and resolved in-memory configuration, bound to the instance and initialization epoch |
| Validated source-bound receipts | Only the exact capability and configuration bindings they actually prove; no current-proof promotion from historical success |
| Private credentials/operator journals | Existing guarded readers; a retained object does not waive provenance or expiry checks when it reopens storage |
| Untrusted filesystem paths | No authority; return blocked/unknown |
| Public HTTP callers and metadata | No privileged host evidence or caller authority |
| Model task text/output | Strict task requirements only; no runtime, proof, approval, epoch or host-fingerprint assertions |

No private credential, operator, probe or config path is copied, re-signed or
blessed. Existing expiry, revocation, full-enrollment and source-binding rules
continue to apply. No new approval, credential, enrollment or task is created.

### Native bridge boundary

The bridge accepts a genuine already initialized `AgentBridge` owned by the
server's existing `Bridge`. It verifies the exact registry/router/initializer
relationships and an initialization anchor established by successful normal
initialization. Instance, process and initialization epoch are checked on each
observation and revalidation. Old objects without that anchor are rejected;
there is no retroactive registration or caller-supplied replacement epoch.

The reader does not call lazy `Bridge.get_agent_bridge()`, registry reconstruction,
`get_agent()`, model or memory constructors. It derives sanitized metadata from
the retained registry, current effective configuration and already cached model
state. A configured route must be distinguished from a cached session/fallback
route; ambiguity remains unknown. It never reads messages, prompts or memory.
Configuration and enabled-state drift invalidate retained observations.

Caller evidence must come from an actual active execution scope bound to the
same owner, Agent, delegate tool, Context and session. A context variable or
`tool.current_context` alone is insufficient: the latter can survive a completed
turn. The normal reply lifecycle must invalidate the scope in `finally`.
Use existing native delegation policy and authority intersection functions.
Evaluate team, depth, cycle and allowed-target rules only from resolved current
state with established provenance. Missing session/team/receiver evidence stays
unknown; no supplied caller dictionary or file fallback fills the gap. Any small
pure-function extraction must retain existing execution semantics and must not
create another policy engine or registry.

The implementation retains an immutable receipt of the existing successful
`apply_session_prefs` operation, bound to its Agent, session and owner. Discovery
does not reread that file. Failed or reapplied preferences invalidate the old
receipt. The root reply scope derives its speaker and zero-depth lineage from
the actual routing/cache binding and checks for a preexisting ambient parent run;
asserted or inherited nested ancestry cannot supply a root grant.
An unrelated cached persistent Agent cannot establish an isolated receiver's
project or permission boundary.

Only internal trusted server code may construct or invoke this factory. No new
HTTP route, tool argument, debugger injection, credential or externally callable
bootstrap is added. This is an application trust boundary, not a sandbox against
arbitrary code already executing in the server's address space.

### Admission and private authority

Retained recovery liveness and existing busy locks may provide bounded partial
observations. They do not prove free capacity, and the bridge must not create or
open a task store, reserve a slot or write an intent to discover capacity.
Unknown capacity stays unknown. Observation lifetimes remain at most 30 seconds.
Selection and revalidation cannot dispatch or contact an adapter implicitly.

Named/external bindings continue through the existing authenticated inspection
and private journal contract. In-process native state does not authenticate an
external approval or probe. The new initialized factory conservatively leaves
external native snapshot/proof unavailable. It never calls the disk snapshot
reader, which hashes config, private environment and source files; the process
view cannot authenticate those inputs or attest the adapter's loaded code.
Guarded journal expiry observations remain available before that limit. The
legacy host path is unchanged. Keep `native_isolated`, `persistent_named` and
`external_runtime` separate.

### Existing process deployment limit

Source inspection found `web.application(..., autoreload=False)` in
`channel/web/web_channel.py` and no supported authenticated hook that can install
or invoke this new bridge inside the existing PID. `/api/agents` is file-derived;
model catalogs are declarations; chat/task endpoints dispatch. None is a safe
bootstrap. Writing new source cannot prove the old process has loaded it.

The authorized source implementation can therefore be validated independently,
but live A/B cannot be claimed unless an existing safe ingress and provenance
are actually established. No restart, replacement process, public-API promotion,
debugger attachment or manufactured initialization anchor will be used to force
a pass. A fresh disposable Python process is only a test fixture.

## Implementation and verification plan

1. Publish this decision and baseline on PR #4 before production edits.
2. Add `agent/discovery/initialized_runtime.py`, normal initialization/active-turn
   hooks in `bridge/agent_bridge.py`, and a host factory in
   `agent/discovery/runtime_readers.py`. Use only narrowly necessary existing
   policy helpers; preserve private filesystem guards.
3. Add independent tests in `tests/test_discovery_in_process.py`: valid normal
   initialization plus unauthorized/forged owner, identity/caller substitution,
   stale epoch/PID, config/disabled/model drift, private memory isolation,
   unknown proof, expired authority, unavailable/stale admission, revalidation,
   no fallback, zero creation/dispatch and unchanged filesystem rejection.
4. Run focused discovery/native authority/bridge regressions. Obtain one
   independent high-reasoning security review before any live acceptance attempt.
   Correct actionable findings and retest affected paths.
5. Run hosted macOS Python 3.13, Linux Python 3.11/3.13, JavaScript, strict
   TypeScript, desktop build and Ruff. Record source and receipt hashes.
6. Evaluate live feasibility after review. Use only the existing process and
   existing authority records; retain an honest blocked receipt if no trusted
   ingress exists. Record A–J separately from disposable test coverage.
7. Publish results, independent no-dispatch observations, CI and review receipts;
   update README and the handoff. Verify upstream 0/0 and keep PR #4 draft.

The lead owns integration, documents, live feasibility and Git. The existing
Sol 6.1/high implementation worker owns the bounded production boundary: Luna
is insufficient for the interacting instance/caller/private-proof trust analysis.
Luna/high owns independent tests and preservation metadata. A separate Sol
6.1/high reviewer will assess the same security-sensitive boundary once, before
live testing. Requested models are recorded; effective-model attestation is not
exposed by this runtime. No external worker pool or HomeBoss is used.

## Acceptance status at decision publication

| Scenario | Current status; required final evidence |
| --- | --- |
| A: native identities | Pending trusted in-process observation; public IDs are not sufficient |
| B: native caller | Pending; no trusted active caller obtained; do not create a task |
| C: TestPilot | Pending fresh guarded expiry evaluation; existing authority only |
| D: TestPilot2 | Pending independent evaluation and identity/workspace ownership binding, without memory contents |
| E: external Codex | Preserve actual enrolled runtime ID `acceptance-runtime`; no general-coding inference |
| F: proof | Rejected-path/stale-proof behavior must remain deterministic |
| G: missing approval | Disposable missing/revoked/expired distinctions; no live requests |
| H: unavailable runtime | Missing/expired admission cannot make a candidate eligible; no process termination |
| I: revalidation | Current trusted state where available; isolated disposable drift elsewhere |
| J: zero dispatch | Independent before/after aggregate metadata and instrumented source tests; do not claim unrun live integration |

No 002R implementation, new CI result or successful live integration is claimed
by this initial decision. The final report will explicitly classify the outcome
as PASSED, PARTIAL or BLOCKED under the maintainer's contract.
