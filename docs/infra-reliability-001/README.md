# INFRA-RELIABILITY-001

Status updated by INFRA-RELIABILITY-001B: the owner removed Projects from pCloud
Backup. The [removal and integration addendum](backup-removal-verification.md)
records current evidence and supersedes the earlier Git migration proposal.
Independent integration review passed and PR #2 merged as `323fefcd`. Git,
runtime and automatic master CI postflight passed. See the addendum for receipts.

Repository: hottweelz/CowAgent. Baseline master:
`fe00855a9f7b896115b2268492e11aa82d9bdc10`.
Branch: `codex/infra-reliability-001`.
Review: [PR #2](https://github.com/hottweelz/CowAgent/pull/2).

| Issue | Assessment | Evidence and remaining limit |
| --- | --- | --- |
| Git reference integrity | **RESOLVED for the known active backup exposure** | Projects is absent from Backup, Sync is empty, all configured roots exclude the checkout/runtime, and Git integrity checks pass. Historical writer attribution remains unknown. |
| GitHub Actions execution | **CONTAINED** | Manual dispatch and automatic PR events produced completed hosted jobs with retrievable logs. The final quality matrix passed. The historical missing-event cause remains unknown. |

**BullGod development readiness: Yes.** Normal integration, operational
postflight and automatic master CI passed. This task did not implement BullGod
discovery/task selection or activate production orchestration.

## Initial state and preserved evidence

[baseline.json](baseline.json) records matching local HEAD/master/origin/master
and the published baseline, upstreams, remotes, worktrees, allowlisted Git
configuration, files-ref storage, reflog entries, metadata hashes and lock state.
Tracked files were clean. All seven pre-existing untracked files are preserved.
The original CowAgent listener remained PID 28093 at 127.0.0.1:9899.

The previous recovery refs and five-entry conflict backup manifest were checked;
every preserved artifact matched its recorded SHA-256. `git fsck --full` passed:
40 dangling objects, no other errors, and no pruning or cleanup. See
[git-object-check.json](git-object-check.json). The second worktree is a
detached temporary checkout with shared metadata under `.git/worktrees/source`.
No reset, history rewrite, forced push, conflict deletion or live SQLite repair
has been used.

## Git findings

The checkout and common Git directory are on local APFS, outside the pCloud Drive
mount. That does **not** place them outside pCloud Backup.

The original read-only macOS Accessibility inspection showed an active Backup for
`/Volumes/Predator SSD GM7 1TB/Projects`, which contains CowAgent and `.git`.
The Sync tab had no rows. Current folder/file exclusions do not cover `.git`.
The app warns that exclusions do not affect content already included in Backup.
See [pcloud-scope.json](pcloud-scope.json). Unrelated account fields and backup
roots are omitted from the published inventory.

[pCloud's guidance](https://help.pcloud.com/article/files-not-recommended-for-sync-backup-or-uploads)
explicitly warns against synchronizing active `.git` metadata and describes
conflicted copies from frequently changing files. Its
[Backup guide](https://help.pcloud.com/article/using-back-up-in-pcloud-drive)
describes continuous synchronization. This supports pCloud Backup as the leading
cause. It does not identify the process that performed each historical ref write.
The previously observed conflict-copy spelling differs from the vendor example.

A scoped open-file sample found no current CowAgent handle in pCloud; it cannot
exclude transient access. See [pcloud-open-file-sample.json](pcloud-open-file-sample.json).
The main pCloud database was locked during two read-only schema attempts. No
account/token/file-index data were read or exported. macOS process attribution
through fs_usage requires administrator privileges; non-interactive sudo is not
available. A short clean observation is not evidence that the writer is absent.

GitHub Desktop, VS Code and Codex were running, but no captured evidence assigns
the conflict to those clients. The one linked worktree is recorded and must
remain usable through any approved migration.

## Original migration rehearsal (superseded)

A metadata-only move outside active backup roots was rehearsed. Candidate: `$HOME/Library/Application Support/CowAgentGit/CowAgent.git`.
The separate-directory rehearsal failed the main-worktree reporting/repair gate.
Git 2.50.1 derives that path from its common directory rather than core.worktree.
An experimental bare-common topology preserved data but required manual metadata
changes during rollback; it is not a validated live procedure. A controlling
`.git` pointer would also remain exposed to Backup. See the
[migration plan](migration-plan.md) and [rehearsal receipt](migration-rehearsal.json).
No live migration was performed or requested for approval from this failed plan.

The bounded, read-only polling monitor passed four focused tests, including a
linked worktree and conflict detection that remains latched after removal. It
records ref changes and invalid conflict names, enforces expected commit IDs,
and never repairs refs. A 45-second live observation around fetch and a detached
worktree status check recorded no change; see [git-observation.json](git-observation.json).
Polling cannot attribute a writer or guarantee detection of between-sample
transients. Privileged attribution remains a separate operator-run procedure.

## GitHub Actions investigation

[actions-baseline.json](actions-baseline.json) records enabled Actions, recognized
active workflows, read-only default token permission, matching event definitions
and zero historical run/check records. No disabled workflow, obvious filter,
skip annotation or protection rule explained those missing runs. Account policy
and GitHub backend event diagnostics were not available; no billing cause is
asserted.

A controlled REST dispatch of the existing Windows Bash workflow received HTTP 204
([dispatch receipt](actions-dispatch-1.json)), created
[run 42534178341](https://github.com/hottweelz/CowAgent/actions/runs/42534178341),
started a hosted runner and completed successfully. The logs were retrieved:
**11 passed, 5 skipped**. [Full receipt](windows-hosted-run.json).
This is limited Windows Bash coverage, not a full Windows regression.

Opening PR #2 triggered the new Tests workflow automatically:
[run 42534913045](https://github.com/hottweelz/CowAgent/actions/runs/42534913045).
This run exposed four unique fixture/timeout failures; its exact logs are retained
in [attempt 1](hosted-matrix-attempt-1.json). A second automatic run passed macOS
but exposed Linux reaping during a proc-file read; see
[attempt 2](hosted-matrix-attempt-2.json). Manual and PR event creation now work;
the earlier zero-run cause remains unexplained.

## CI quality gate

The integrated Tests workflow defines one ordinary matrix: macOS/Python 3.13,
Linux/Python 3.11 and Linux/Python 3.13. Full pytest collection includes existing
security and authority tests without a duplicate security suite. Separate jobs
run web/desktop JavaScript tests, strict desktop TypeScript/build and changed-file
Ruff F checks. Dependency caches and JUnit artifacts use existing project specs.
Explicit test prerequisites include ripgrep, the public tokenizer cache, local
synthetic tokenizers/templates and four supported document parsers. JUnit showed
29 missing-ripgrep skips in the first matrix; setup now installs/verifies it.
Unrelated optional SDK pins are not installed.

Jobs request only contents:read; checkout credentials are not persisted. No model
credentials, private data, production state, service address or native acceptance
is supplied to hosted CI. The Python runner clears inherited environment before
collection, uses private HOME/data paths, and allows only Python socket calls to
owned local fixtures. It denies port 9899 and external connections. This is Python
instrumentation, not OS confinement of native libraries or subprocesses. Hosted
runners have no connection to the personal CowAgent workspace. Native model
acceptance and browser integration remain separate from ordinary PR checks.
The three optional Playwright cases launch real Chrome, so Playwright
is not installed in ordinary jobs; the twelve native browser opt-in cases also
stay disabled. These exclusions are reported, not counted as passed.

The changed-file lint gate fails on an invalid base and handles path whitespace
and deletions. Manual Tests dispatch requires an explicit full base commit SHA.
The supported public tokenizer asset is fetched before guarded test execution;
SQLite 3.44+ is checked explicitly. Python dependency ranges remain floating, as
in the existing project; npm uses its committed lockfile.

## Demonstrated repairs

- A bound Unix socket file is not a listening endpoint. The IPC fixture now waits
  for a successful connection, retaining its authenticated protocol assertions.
- A killed Linux orphan may be a zombie before PID1 reaps it. The cleanup fixture
  rejects runnable/stopped live states and accepts only missing or terminal Z/X
  states. It also handles ESRCH during `/proc` read; a deterministic test proves
  this race and another proves a live state remains rejected.
- Recovery can finish timed_out before the parent pool deadline. The subagent
  runner now supplies a missing timeout diagnostic before closing the run or
  emitting the state/UI callback, preserving any more specific existing error.
  The deterministic test covers the returned value, callback and two UI cards.
  No routing, memory, model/provider or permission decision changed.

Focused checks passed: CI runner 4, watcher 4, IPC/client 32, timeout-related 82 plus
2 expanded cases, final client 9, and local-tokenizer/cache 6. Changed-file Ruff and
YAML checks passed. Failed intermediate evidence is retained.

## Final hosted validation

[Run 42536883493](https://github.com/hottweelz/CowAgent/actions/runs/42536883493)
was automatically triggered by PR synchronization at implementation commit
[`c03d35e6`](https://github.com/hottweelz/CowAgent/commit/c03d35e6fd0ca1f35ad125b881db39816090951c).
All five jobs completed successfully; all logs and three JUnit archives were
retrieved and reconciled. [hosted-final.json](hosted-final.json) records job IDs,
events, step status, archive/XML/log hashes, counts and individual skip reasons.

| Gate | Result |
| --- | --- |
| macOS, Python 3.13 | 5,917 passed; 39 skipped; 93 subtests passed |
| Linux, Python 3.11 | 5,910 passed; 46 skipped; 93 subtests passed |
| Linux, Python 3.13 | 5,910 passed; 46 skipped; 93 subtests passed |
| JavaScript | 39 web and 5 desktop tests passed |
| Desktop | Strict TypeScript check and build passed |
| Static checks | Changed Python files passed Ruff F checks |

Each Python job collected 5,956 named cases from 708 tracked test files. JUnit
contains 6,049 entries including the 93 subtests. macOS skips comprise 24
Windows-only and 15 browser integration cases. Each Linux job adds 7 macOS or
filesystem-specific skips. Missing search/tokenizer/parser prerequisites no longer
remove coverage. Existing warnings and background cleanup diagnostics remain in
the logs; this is not a claim that those diagnostics are absent.

[validated-source.json](validated-source.json) freezes all eleven changed
implementation, test, dependency and workflow files. The closing documentation
commit uses `[skip ci]` to avoid rerunning this valid matrix for receipts alone;
its implementation hashes must remain identical. It is not a separate CI pass.
That receipt covers the original branch gate. The addendum records subsequent
integration; no separate run is attributed to documentation-only commits.
No live model acceptance was replayed. Earlier native approvals bind their own
source and are not represented as acceptance for this changed source.

## Recovery and final decision

[recovery.md](recovery.md) defines bounded monitoring, optional administrator PID
attribution, evidence-preserving ref repair and rollback limits. It prohibits
reset/force-push/deletion and explains why an old snapshot alone is insufficient
for rollback after newer commits.

The [original independent review](review.md) covered source and hosted receipts.
The [001B integration review](backup-removal-review.md) verifies the owner-removed
backup exposure, current Git/runtime state and unchanged tested source. Under the
001B definition, the known active backup exposure is RESOLVED. Actions remains
CONTAINED; historical writer and missing-event causes remain unknown.

The repository stays at its existing path. The owner's removal of the Projects
backup supersedes migration. Follow the [addendum](backup-removal-verification.md)
for integration/postflight results. Retain monitoring and recovery instructions
for future incidents, without treating a clean poll as a guarantee.

## Evidence inventory

| Evidence | Receipt |
| Current backup removal and integration gates | [001B addendum](backup-removal-verification.md), [001B review](backup-removal-review.md), [master CI](backup-removal-master-hosted.json) |
| --- | --- |
| Initial refs, configuration, filesystem, worktrees and preserved files | [baseline](baseline.json) |
| Active backup scope and bounded process sample | [pCloud scope](pcloud-scope.json), [open-file sample](pcloud-open-file-sample.json) |
| Failed disposable migration and rollback gates | [plan](migration-plan.md), [rehearsal](migration-rehearsal.json) |
| Controlled ref observation and object integrity | [observation](git-observation.json), [fsck](git-object-check.json) |
| Live Actions policy and workflow recognition | [baseline](actions-baseline.json) |
| Accepted dispatch, runner execution and Windows logs | [dispatch](actions-dispatch-1.json), [Windows receipt](windows-hosted-run.json) |
| Retained failed hosted attempts and prerequisite repairs | [attempt 1](hosted-matrix-attempt-1.json), [attempt 2](hosted-matrix-attempt-2.json), [prerequisites](hosted-prerequisites.json) |
| Final source and hosted success | [source hashes](validated-source.json), [final receipt](hosted-final.json) |
| Prepublication refs, source, file preservation and original listener | [closeout verification](closeout-verification.json) |
| Independent review and operational recovery | [review](review.md), [recovery](recovery.md) |

GitHub links and sanitized receipts are durable branch records. Local raw logs,
archives and disposable fixtures are retained at the receipt paths; temporary
storage and GitHub artifact retention are finite. No signed download URLs or
credential values are published.
