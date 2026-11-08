# INFRA-RELIABILITY-001

Status: investigation and validation in progress. Do not merge this branch.

Repository: hottweelz/CowAgent. Baseline master:
`fe00855a9f7b896115b2268492e11aa82d9bdc10`.
Branch: `codex/infra-reliability-001`.
Review: [PR #2](https://github.com/hottweelz/CowAgent/pull/2).

## Initial state and preserved evidence

[baseline.json](baseline.json) records matching local HEAD/master/origin/master
and the published baseline, upstreams, remotes, worktrees, allowlisted Git
configuration, files-ref storage, reflog entries, metadata hashes and lock state.
Tracked files were clean. All seven pre-existing untracked files are preserved.
The original CowAgent listener remained PID28093 at 127.0.0.1:9899.

The previous recovery refs and five-entry conflict backup manifest were checked;
every preserved artifact matched its recorded SHA-256. The second worktree is a
detached temporary checkout with shared metadata under `.git/worktrees/source`.
No reset, history rewrite, forced push, conflict deletion or live SQLite repair
has been used.

## Git findings

The checkout and common Git directory are on local APFS, outside the pCloud Drive
mount. That does **not** place them outside pCloud Backup.

Read-only macOS Accessibility inspection of pCloud showed an active Backup for
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

## Proposed containment and recovery

A metadata-only move outside active backup roots is being rehearsed before any
approval request. Candidate: `$HOME/Library/Application Support/CowAgentGit/CowAgent.git`.
The checkout path would stay fixed. A main `.git` pointer and linked-worktree
pointers need verification, as do per-machine portability and rollback that
preserves commits made after migration. Live migration is not yet authorized.

A bounded, read-only polling monitor is being tested. It records ref changes and
invalid conflict names, can enforce expected commit IDs, and never repairs refs.
Polling cannot attribute a writer or guarantee detection of between-sample
transients. Privileged attribution remains a separate operator-run procedure.

## GitHub Actions investigation

[actions-baseline.json](actions-baseline.json) records enabled Actions, recognized
active workflows, read-only default token permission, matching event definitions
and zero historical run/check records. No disabled workflow, obvious filter,
skip annotation or protection rule explained those missing runs. Account policy
and GitHub backend event diagnostics were not available; no billing cause is
asserted.

A controlled REST dispatch of the existing Windows Bash workflow received HTTP204
([dispatch receipt](actions-dispatch-1.json)), created
[run42534178341](https://github.com/hottweelz/CowAgent/actions/runs/42534178341),
started a hosted runner and completed successfully. The logs were retrieved:
**11 passed, 5 skipped**. [Full receipt](windows-hosted-run.json).
This is limited Windows Bash coverage, not a full Windows regression.

Opening PR #2 triggered the new Tests workflow automatically:
[run42534913045](https://github.com/hottweelz/CowAgent/actions/runs/42534913045).
Final conclusions and logs are pending. Manual and PR event creation now work;
the earlier zero-run cause remains unexplained.

## CI quality gate

The existing Tests workflow now defines one ordinary matrix: macOS/Python3.13,
Linux/Python3.11 and Linux/Python3.13. Full pytest collection includes existing
security and authority tests without a duplicate security suite. Separate jobs
run web/desktop JavaScript tests, strict desktop TypeScript/build and changed-file
Ruff F checks. Dependency caches and JUnit artifacts use existing project specs.
Four supported document parsers supplement core requirements; unrelated optional
SDK pins are not installed.

Jobs request only contents:read; checkout credentials are not persisted. No model
credentials, private data, production state, service address or native acceptance
is supplied to hosted CI. The Python runner clears inherited environment before
collection, uses private HOME/data paths, and allows only Python socket calls to
owned local fixtures. It denies port9899 and external connections. This is Python
instrumentation, not OS confinement of native libraries or subprocesses. Hosted
runners have no connection to the personal CowAgent workspace. Native model and
browser opt-in acceptance remains separate from ordinary PR checks.

The changed-file lint gate fails on an invalid base and handles path whitespace
and deletions. Manual Tests dispatch requires an explicit full base commit SHA.
The supported public tokenizer asset is fetched before guarded test execution;
SQLite3.44+ is checked explicitly. Python dependency ranges remain floating, as
in the existing project; npm uses its committed lockfile.

## Review and final decision

Independent engineering review, final validation receipts, per-issue
classification and the BullGod readiness decision are pending. This assignment
does not implement agent discovery or task selection, activate orchestration,
change TestPilot identities/memory/models, or restart CowAgent.
