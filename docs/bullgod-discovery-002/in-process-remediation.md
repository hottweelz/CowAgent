# BULLGOD-DISCOVERY-002R — trusted in-process integration

**Current outcome: BLOCKED for actual live integration.** The source bridge is
implemented at `209f4e0fd53aeb249914755a68a1956d9e6225a0`, with 345 focused tests
passing and independent review PASS. The original service has no verified safe
path to load or invoke the new bridge under the no-restart constraint. This is
not a PASSED or PARTIAL live-native result. The full hosted gate is also BLOCKED:
GitHub failed to acquire a macOS runner on both the original attempt and one
targeted retry. Both Linux jobs, JavaScript/TypeScript/build and Ruff passed.

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

## Actual observations and A–J results

The source implementation and its tests are published under the existing draft
PR #4; a separate review boundary was unnecessary. The
[live feasibility receipt](in-process-live.json) stops at
`existing_process_trusted_ingress`. The original PID was not replaced or injected.
No new host was constructed as a stand-in for that service. A fresh metadata-only
mount check still returns `filesystem_ownership_ignored` before private content
can be read. The source fingerprint belongs to the tested checkout; it is not
an attestation of code loaded in the old PID.

The [fresh authority receipt](in-process-authority.json) separately checks the
existing private operator journals through their original guarded, read-only
reader. These are actual current journal observations, not full integrated
candidate decisions. All three credentials, enrollments and exact task approvals
remain expired. The historical tasks already have submission started and cannot
be replayed. No probe, native config, private memory or socket was read/contacted
by that authority inventory.

| Scenario | Actual live result | Source/disposable verification |
| --- | --- | --- |
| A: actual native identities | BLOCKED: public metadata lists default/testpilot/testpilot2, but no trusted original-process registry observation was possible | Normal Bridge/AgentBridge initialization supplies actual retained registry; forged owner, stale PID/epoch and mismatched registry reject |
| B: native caller | BLOCKED: no trusted active caller obtained; no task created to obtain one | Active root scope evaluates existing team/ACL/depth/cycle policy; stale/substituted caller and inherited/unproven lineage reject or remain unknown |
| C: TestPilot | Guarded current credential/enrollment/task state all expired for cowagent.testpilot; integrated native binding unverified | A current disposable journal is observed without authenticating unavailable native proof |
| D: TestPilot2 | Independently expired for cowagent.testpilot2; distinct retained identity and baseline workspace/profile metadata, without reading memory; trusted live in-process ownership binding unavailable | Native registry ownership and cross-agent private exclusions retained; private Agent state access is forbidden during observation |
| E: external Codex | Actual retained runtime ID remains acceptance-runtime; credential/enrollment/task state expired; no executable/model attestation attempted | Existing external_runtime mechanism remains analyze_records-only; no general-coding promotion |
| F: proof | Native proof unavailable; ignored-ownership source remains rejected; historical success not refreshed | Existing stale/incomplete/provenance tests retained; new initialized factory refuses disk native snapshot proof |
| G: missing approval | Actual records are expired, not missing; no approval request created | Existing disposable missing/expired/revoked distinctions remain covered; new private journal binding is independently exercised |
| H: unavailable runtime | No fresh authenticated admission observed; native health/capacity remain unknown; no process terminated | Existing freshness/unavailable tests pass; new view never infers capacity from an unlocked mutex or creates a store |
| I: revalidation | No selected live candidate; integrated live revalidation cannot be claimed | Current config/route/caller/epoch changes invalidate observations; existing selected-then-drift tests pass |
| J: zero dispatch | No in-process acceptance was invoked. Guarded inventory made zero socket contacts, writable DB opens or SQL writes; independent preservation comparison recorded separately | New lifecycle tests forbid constructors, dispatch and private Agent access; full acceptance is not inferred from unchanged counts |

## Validation and independent review

[Focused receipt](in-process-focused.json): **345 passed, zero failures/errors/
skips**, including all 20 new in-process cases. The selected suites cover discovery,
existing readers/acceptance, native authority/delegation, protected files, bridge
lifecycle/singleton, multiple agents, direct addressing and model fallback.
Tests run through the isolated `scripts/ci_test.py` wrapper. Compilation, Ruff F
and diff whitespace checks pass.

The [independent source/test review](in-process-review.md) reports **PASS** after
three bounded findings were corrected: coherent route/policy snapshot, inherited
ambient-parent handling, and stale-owner validation before explicit adapter
contact. Self-review also removed a path helper's directory-creation side effect.
The reviewer independently checked AST/whitespace and inspected the final tests;
it did not duplicate pytest or perform live calls.

Tested native source fingerprint:
`1ecd417849013c817087d6b30aab0c485b3853a724ba2f53634c978a1e257731`.
Exact changed-source/test and log/XML hashes are retained in the focused receipt.
The source commit is `209f4e0fd53aeb249914755a68a1956d9e6225a0`, tree
`00b14af2a2b2e0c54c5bf5cdee34d124e6501d35`.

Hosted validation: **BLOCKED — macOS runner acquisition**.
[Run 42660051257](https://github.com/hottweelz/CowAgent/actions/runs/42660051257)
completed with four passing jobs and an unexecuted macOS requirement. The
[hosted receipt](in-process-hosted.json) retains both attempts and exact source,
checkout-tree, log/artifact/XML and test-identity bindings.

| Required hosted job | Result on source 209f4e0f |
| --- | --- |
| macOS Python 3.13 | BLOCKED: jobs 129308863500 and targeted retry 129319168938 cancelled before any runner assignment or step |
| Linux Python 3.11 | 6,036 passed, 46 skipped; 93 passing subtests |
| Linux Python 3.13 | 6,036 passed, 46 skipped; 93 passing subtests |
| JavaScript / strict TypeScript / desktop build | Passed |
| Ruff | Passed |

Each Linux XML has 6,082 named cases: exactly 20 new in-process cases, no removals,
and the same skip identities as prior accepted run 42558258829. All new cases
pass. GitHub's two macOS annotations state that no hosted runner could be acquired
after multiple attempts and cite macOS arm64 capacity constraints. Neither job
had a runner or steps; logs were unavailable with BlobNotFound. There is no macOS
full-regression result for this source. This was infrastructure acquisition
failure, not a test assertion failure.

The lead requested only one targeted retry of the cancelled macOS job.
GitHub carried forward the four successful records with their original run
times, runner identities, steps and artifacts. Source and workflow remained
unchanged. After the same failure recurred,
no further rerun, runner substitution or workflow change was attempted. A future
successful hosted macOS run on this exact source, or justified new-source gate,
remains necessary. Local focused tests and older macOS receipts do not replace it.
Hosted fixture results also cannot substitute for actual live integration.

## No-dispatch evidence and limits

The existing service was not restarted, stopped or replaced. Profiles, model
settings, mounts, volume permissions, live credentials and approvals were not
changed. No private memory content was read or hashed. The [independent preservation receipt](in-process-preservation.json) confirms
PID/start time/health, config/profile/model/workspace metadata and aggregate
conversation/operator/recovery counts match the fresh baseline. All seven
original files, recovery refs/artifacts and the clean detached worktree remain
intact. These before/after checks are not a byte-level
memory comparison or universal audit of unrelated concurrent activity.

The separate guarded authority observer blocked process/socket creation and
required SQLite `mode=ro` plus `query_only`. One dependency import attempted
`croniter.is_32bit -> platform.architecture -> file`; the observer rejected
`Popen` before launch. The receipt records one blocked process attempt and zero
launched processes. It was not a model/runtime command. A bounded traceback-only
reproduction identified the import caller; no task was replayed. Logging artifacts
are kept separately from live task, model, publication and conversation state.

## Final ten answers

1. **Can the actual process supply trusted registry/config evidence?** Not through
   a supported verified ingress available under this task's constraints. The new
   source path can do so in a normally initialized runtime that has loaded it.
2. **Can evidence be bound to runtime/authority?** Source tests prove the new
   instance/PID/epoch and active-object binding. It is not established in the old PID.
3. **Can real TestPilot/TestPilot2 be evaluated without private memory access?**
   Their existing authority expiry and distinct retained IDs were evaluated safely.
   Full integrated native identity/memory-ownership evaluation remains blocked.
4. **Can current external enrollment/approval be read safely?** Yes, for the
   retained private stores on ownership-enforced storage; all three are expired.
5. **Does ignored-ownership evidence remain rejected?** Yes. The actual mount
   still rejects, and the new native view does not waive private-file provenance.
6. **Are expired credentials, approvals and proofs classified correctly?** Actual
   credentials/approvals remain expired. Current native proof is unavailable;
   stale/incomplete proof handling passes in disposable tests. No proof is renewed.
7. **Are the three mechanisms preserved?** Yes: native_isolated, persistent_named
   and external_runtime remain distinct, with no automatic weaker fallback.
8. **Can actual candidate eligibility be computed without invention?** Current
   expired authority supports ineligibility, but full live discovery was not run.
   The implementation denies/returns unknown when evidence is absent.
9. **Is zero dispatch independently verified?** The source path and guarded
   inventory made no dispatch; independent metadata comparisons bound the observed
   effects. This does not claim completion of unrun integrated live acceptance.
10. **What is needed before authorized BullGod execution?** A separately permitted
    way to load and invoke the reviewed bridge in the real service, successful
    trusted live acceptance, current authentic proof/enrollment/exact approvals,
    receiver authority, fresh authenticated admission, a successful required
    hosted macOS regression, and explicit activation authority. This report authorizes none of those changes.

PR #4 remains draft and unmerged. The live milestone is incomplete; an authorized
future loading path is required. Ownership changes, restart, task bootstrap and
production activation are deliberately excluded by the task contract.
