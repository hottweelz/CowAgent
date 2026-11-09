# INFRA-RELIABILITY-001B: backup removal and integration verification

The owner removed the Projects directory from pCloud Backup. This replaces the
previous migration proposal. The checkout, Git metadata, worktrees and runtime
paths stay in place. Historical cloud backups and unrelated pCloud settings were
not changed by this task.

All premerge checks and the independent integration review pass. Normal PR #2
integration is authorized; merge and postflight results will be recorded below. Baseline master is
`fe00855a9f7b896115b2268492e11aa82d9bdc10`; inspected published PR head is
`2502693ae2f87bdb825f4b03ad94d04a082226be`.

## pCloud configuration and coverage

The earlier [scope receipt](pcloud-scope.json) showed seven Backup rows and two
active roots, including `/Volumes/Predator SSD GM7 1TB/Projects`. That root covered
both CowAgent's `.git` and its `CowAgent-TestData` directory.

The [new pCloud receipt](backup-removal-pcloud.json) records supported desktop
settings inspected through macOS Accessibility:

- Projects is absent from Backup, rather than present with an inactive status.
- Six Backup rows remain; one unrelated root is active. The local path of every
  row, including inactive rows, was read from the UI Help property and resolved
  before comparison. No parent, child or overlapping path includes the checkout
  or its Git metadata.
- Sync contains zero rows. There is no configured Sync pair for the checkout,
  its metadata or any overlapping parent.
- Closing and reopening the normal settings window, then revisiting both tabs,
  produced identical Backup rows and zero Sync rows. pCloud PID 891 was not
  restarted. The window was returned to its original closed state.
- The active data directory and all three agent workspaces also have zero
  overlap with the remaining active roots. Unrelated root names and account
  fields are omitted from published receipts.

This directly verifies removal of the configured Backup/Sync relationship.
[pCloud documents Backup as continuous synchronization of selected folders](https://help.pcloud.com/article/using-back-up-in-pcloud-drive).
The configured coverage is unambiguous. A supplemental read-only configuration
database query remained locked; no lock bypass or database copy was attempted.
No kernel-level inventory of every filesystem watch is claimed. In particular,
absence of an open file handle was not used to infer absence of monitoring.

## Git reference integrity

[Git preflight and postflight snapshots](backup-removal-git.json) record:

- Correct branch HEAD, local and tracking master, upstream and recovery refs.
  Published master and local master remain the expected baseline.
- All 177 effective refs agree with Git resolution, using normal loose-ref
  precedence over packed refs. No invalid conflict ref or ref lock was present.
- `git fsck --full` exited 0 with 40 dangling entries and no other errors. No
  prune or garbage collection was run; dangling objects were preserved.
- The existing monitor ran for 45 seconds at a 0.25-second interval around a
  fetch with pruning and automatic maintenance disabled, plus worktree/status
  inspection. It returned 0, with no ref change, conflict or expected-ref mismatch.
  Full pre/post snapshots agree.
- The existing detached worktree remains registered at its original path and
  commit `c2c39a2e0823f1556ecdc79f9e07911fff207a05`, with clean tracked content.
- All seven original untracked files and all five preserved conflict artifacts
  match their prior hashes. Both recovery branches retain their expected commits.

This establishes integrity during the observed operations. It neither identifies
the historical writer nor guarantees that future corruption is impossible.

## Runtime preservation

The [runtime snapshot](backup-removal-runtime-before.json) uses process metadata,
read-only health/roster/model endpoints, configuration/profile digests and file
stat data. No private memory contents or database rows were inspected.

- Original PID 28093 still listens on `127.0.0.1:9899`; `/api/health` returns
  HTTP 200 with status `ok`.
- `COW_DATA_DIR` remains `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData`.
  The main workspace remains `/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace`;
  TestPilot workspaces remain its `agents/testpilot` and `agents/testpilot2` children.
- `default`, `testpilot` and `testpilot2` remain registered and enabled. Current
  configuration bytes match the earlier routing preflight hash. Both named-agent
  profile digests match the earlier native receipt, including model overrides.
- The global model overview remains `nvidia/nemotron-3.5-super-vl:free` with
  provider `custom`. No model/provider configuration was changed.
- Four unique SQLite files exist at their expected workspace paths. Core profile
  file sizes and modification times match retained evidence. Historical receipts
  lack database inode records, so historical inode continuity is not claimed.
  Current inode metadata is retained for comparison after integration.

No service restart, model execution, profile edit, memory reset or relocation
occurred. Integration changes the source checkout, not the loaded process state.

## Published PR and hosted evidence

[Live PR verification](backup-removal-pr.json) confirms PR #2 is four commits
ahead of master with no divergence. The published head differs from tested
`c03d35e6fd0ca1f35ad125b881db39816090951c` only in documentation and receipts.
All eleven implementation, workflow, dependency and test hashes match
[validated-source.json](validated-source.json).

[Run 42536883493](https://github.com/hottweelz/CowAgent/actions/runs/42536883493)
still reports success for all five jobs at that tested source:

| Gate | Verified result |
| --- | --- |
| macOS / Python 3.13 | 5,917 passed, 39 skipped, 93 subtests passed |
| Linux / Python 3.11 | 5,910 passed, 46 skipped, 93 subtests passed |
| Linux / Python 3.13 | 5,910 passed, 46 skipped, 93 subtests passed |
| JavaScript | 39 web and 5 desktop tests passed |
| Build/static | Strict TypeScript, desktop build and Ruff passed |

The documentation-only commit `2502693a` has zero check runs/status entries and
used `[skip ci]`; no new hosted pass is attributed to it. Master reports
`protected: false` and no repository rulesets. The connector could not read the
protection-detail endpoint (403); no hidden setting is inferred. A normal merge
must still satisfy GitHub's live checks. No bypass or protection change is allowed.

The existing full hosted evidence remains applicable because executable source
did not change. Browser integration and full Windows validation remain outside
this ordinary gate. No live model acceptance is repeated for infrastructure work.

## Independent review and integration decision

The [independent integration review](backup-removal-review.md) completed with no
actionable finding. One Sol 6.1/high reviewer checked the new coverage evidence,
Git integrity, runtime preservation and applicability of the hosted gate. The new definition of RESOLVED concerns elimination
of the known active backup exposure; it does not require attributing the old
corruption. The historical Git writer and earlier Actions missing-event cause
remain unknown.

**Premerge classification: RESOLVED for the known active pCloud exposure and
current Git integrity.** Actions remains CONTAINED because its historical
missing-event cause is unknown. The reviewer recommends normal integration.

The owner's conditional merge authorization now applies. Normal GitHub merge,
safe local master fast-forward, and postflight ref/worktree/runtime checks remain
to be recorded before claiming completed integration or development readiness.
No migration or BullGod activation is authorized.
