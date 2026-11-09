# FIRST-BOOTSTRAP-001

**Decision: NO-GO — Material unresolved risk. Legacy class C — UNBOUNDED RISK.**

Published as [draft PR #6](https://github.com/hottweelz/CowAgent/pull/6), based on
PR #5. Content commit `ae8d0b57` is synchronized with its named upstream; this
publication note changes documentation only.

The qualification and disposable recovery work is complete. A live maintenance
window is not yet supportable. This is a specific first-bootstrap decision, not
a claim that the old process needs to implement the new drain API.

Three conditions prevent execution:

1. The direct loopback service still admits work. No supported aggregate legacy
   admission control, established gateway block, or accepted operator-only
   exclusion interval exists. A point-in-time absence of connections and pending
   DB rows cannot bound in-memory queues or plugin callbacks.
2. The actual source-mode configuration enables seven plugins. Reproducing those
   enablement flags in the candidate reached health but correctly returned
   `plugin_runtime_untracked`. Successful drain with disabled fixture plugins
   does not qualify this configuration. The new coordinator standards stay intact.
3. Consistent SQLite and file restoration is demonstrated on fictional state;
   a complete, private live-state checkpoint and tested restoration is not yet
   qualified or authorized. The candidate also has no shipped operator invocation
   for its internal drain API. Source rollback alone cannot meet the recovery gate.

The shortest safe next work is to qualify the enabled plugins' callback and
external-work lifetimes and a private operator drain invocation in disposable
tests; resolve the actual backup manifest and offline recovery procedure; then
present one concrete Class B operator-exclusion/interruption policy for explicit
acceptance. Do not disable plugins, weaken the receipt, or repeatedly rerun an
unchanged legacy audit. No live stop/start, ownership change, authority refresh,
production activation or merge was performed.

## Version and live baseline

| Layer | Verified reference | Meaning |
| --- | --- | --- |
| Current master | `f659349785acf98905901a5cc53921436a109dbc` | Known-tested fallback |
| PR #4 | `a507a400985512683c870ef4fe059fa5982ad13e`, based on master | Draft; startup observer/runtime discovery |
| PR #5 | `8d182026be2380fc574eeecd13edcffa5ed1dcb1`, based on PR #4 | Draft; candidate publication |
| Tested candidate executable | `005c1e4805c75017467b817baa2a8bbbe3f7511d`, tree `d9d8c64ef453e4e44860e2516c070258b1957b1d` | Later candidate changes are documentation only |
| Believed launch baseline | `90c3cd8f72ffe7a47cb20925fa538eda479317c6` | Primary HEAD reflog brackets PID startup at this commit; working bytes and loaded modules are not attested |
| Loaded source | **Unknown** | Never equated with HEAD, master or a PR |

[Baseline reconciliation](validation.md) and [machine-readable evidence](baseline.json)
cover hosted runs, review resolutions, ancestry, five preserved recovery artifacts
and seven original untracked files. The startup manifest contains 368 Python files
and has digest `210cece16670f2d7dc39e15eb8d2ea299388170f05f68710afd6968e7159f36f`.

[Live metadata](live-metadata.json) confirms PID 28093, start epoch
1794162129.482237, repository CWD and virtual-environment launcher, selected
environment identity matches, sole process listener `127.0.0.1:9899` and health
200/ok. There were 31 threads, no descendant processes and no established TCP
connections at capture. These observations are not a work census. Source startup
occurred at 2026-11-08 18:22:09 UTC; later source edits did not retrofit the process.

[Current pCloud settings](pcloud.json) show six configured Backup paths with no
overlap with the checkout/data/workspace/worktree roots and zero Sync pairs.
Settings were not changed; the settings window was returned to closed. This is
configuration evidence, not attribution of historical Git writes or a kernel
watch inventory.

## Runtime, effects and preservation

The [runtime inventory](runtime-inventory.md) separates configured, initialized
and active state for web/SSE, chat queues, native/parallel/child work, scheduler,
recovery/verification, evolution, plugins/MCP, external processes, memory and timers.
It identifies supported controls and their limits. The
[startup/shutdown matrix](startup-effects.md) names reads, durable writes,
metadata changes, managed-file replacement and external effects.

Current metadata selects web only, three enabled identities, evolution off,
no configured MCP file and no scheduler task files at the resolved roots.
Seven enabled plugin IDs are `cow_cli`, `Godcmd`, `Keyword`, `Banwords`, `linkai`,
`Role`, `Finish`. Configured availability is not proof of active execution.

[Durable metadata](durable-metadata.json) found four SQLite databases. Global
conversation metadata has 13 sessions, 39 messages and 18 terminal runs; the three
memory indexes each contain one file/chunk. Recovery has two completed tasks and
attempts, two verification records, zero effects and no completed attempt missing
current verification. No bodies, prompts or memory contents were exported.
The missing `testpilot2` merge marker would be added at startup; its secondary
DB has no conversation tables, so the observed state needs no conversation copy.

[Preservation inventory](preservation-inventory.json) records metadata for the
data root, runtime workspace and mutable source-mode plugin directory. No symlink,
unreadable entry or special file was found there at capture. This is not a backup.
The [maintenance procedure](maintenance.md) defines the private closed-interval
checkpoint, exact pinned launch/source restoration commands, checks and aborts.
Existing operator authority remains in place and unconsumed. Actual live copying,
checkpointing and replacement need separate scope and authorization.

## Disposable recovery and validation

The [recovery report](recovery.md), [receipt](rehearsal.json) and self-contained
[rehearsal script](rehearsal.py) demonstrate an ordered modeled-legacy → candidate
→ restored-master fallback on port **19886**, private fictional state and denied
outbound networking. Port **9899** was never used for rehearsal.

The sequence covers native-schema conversation/indexed memory/recovery history,
closed-interval SQLite backups, committed WAL versus uncommitted writes,
authenticated one-use discovery, denied selection without proof, coordinator
initialization, held-work accounting, closed-admission 503, completion and graceful
exit, snapshot restoration and fallback health. Fresh fictional IDs are generated.
Startup interrupted between team and conversation migration restarts successfully;
a separate two-test migration fault suite covers committed-copy/marker retry.
Neither is represented as a process crash in the middle of a transaction.

The enabled-plugin variant preserves the seven enablement flags using fictional
configuration. Its correct failed drain is evidence of the remaining blocker.
Browser launch is replaced in the fixture, and real model/provider/adapter work
is excluded. No general exactly-once or private-live-data recovery claim is made.

Full validated executable evidence is retained without redundant re-execution:
local 6,124 passed / 36 skipped / 93 subtests; hosted Linux 3.11 and 3.13 each
6,114 / 46 / 93; macOS 3.13 6,121 / 39 / 93. JavaScript 39 web + 5 desktop,
strict TypeScript/build and Ruff passed in
[run 42699928448](https://github.com/hottweelz/CowAgent/actions/runs/42699928448).
All platforms reconcile to 6,160 named cases. This milestone changes qualification
documents and standalone fictional fixtures, not runtime, dependencies or CI inputs.
New fixture/procedure checks and independent review are recorded in [review.md](review.md).

## Required final answers

| Question | Answer |
| --- | --- |
| 1. What can PID 28093 execute/admit? | Its web listener remains available. Configured agent turns, parallel children, plugin commands and manual scheduler actions can enter through supported routes. Background maintenance/recovery can run independently. Actual loaded code and active queues are not attested. |
| 2. What active paths are reliably observable? | Listener/process identity, current descendants/connections, persistent run/recovery statuses and configured files. They do not expose every active request, future, plugin callback, memory transaction or detached worker. |
| 3. Can new work be blocked without modifying/restarting it? | Operator client exclusion is possible in principle. No already-established gateway or supported all-producer switch was found. Such exclusion is not currently proven or accepted. |
| 4. What legacy class is justified? | C now. Class B is a future bounded policy option after concrete exclusion, recovery and interruption acceptance; Class A is not supported. |
| 5. What state needs preservation? | All data/workspace roots; global and per-agent DBs and documents; profiles/team/config; recovery/verification; scheduler files; skills/assets; source-mode plugin state; user-data pickle; relevant source/log/PID metadata. Preserve separate authority without rewind. |
| 6. Can it be backed up/restored consistently? | SQLite online backup plus a closed file-set interval works on the tested fictional state. Actual live set completeness and restoration are not yet qualified; no live backup exists from this task. |
| 7. Are migrations compatible with fallback? | Tested native schemas and fictional records survive candidate and restored master. Missing merge-marker retry is idempotent in focused tests. Real-data rollback, asynchronous interruption and external effects remain bounded limits. |
| 8. What effects need acceptance? | Config/team/schema/marker writes, managed skills/assets replacement, indexes and background services, plugin local state and callbacks, browser/external effects, logs/PID and shutdown pickle save. No normal-startup read-only claim. |
| 9. Is the exact launch verified? | Exact candidate/interpreter/helper/authentication/source-selection mechanics are verified on disposable data. Production environment, effects, private recovery and operator drain invocation are not fully qualified. |
| 10. Is full transition reproducible? | Yes for the published self-contained fictional fixture and stated models/limits, including ordered legacy/candidate/restored fallback. It does not reproduce private live state. |
| 11. What remains unique to the legacy process? | No process-owned admission/lease census; unknown loaded modules, transient queues/callbacks/transactions, detached or already-issued effects and inability to recover its in-memory state. |
| 12. Is live maintenance supportable? | Unsafe under the current gate: NO-GO. Resolve the named controls/recovery gaps, then seek a separate bounded maintenance decision. |

## Remaining owner decisions

Any future execution requires explicit acceptance of the concrete client-exclusion
and legacy interruption policy; the qualified private backup/restore manifest;
enumerated startup/shutdown effects; private in-memory environment handling;
candidate/fallback outage bounds; and a specific live stop/start attempt. New
approvals do not replace missing technical qualification. APFS ownership,
production activation and merges remain outside this milestone.
