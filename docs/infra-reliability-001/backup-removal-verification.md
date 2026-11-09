# INFRA-RELIABILITY-001B: backup removal and integration verification

The owner removed the Projects directory from pCloud Backup. This replaces the
previous migration proposal. The checkout, Git metadata, worktrees and runtime
paths stay in place. Historical cloud backups and unrelated pCloud settings were
not changed by this task.

All required premerge checks and the independent integration review passed.
PR #2 merged normally. Local Git/runtime postflight and the automatically
triggered master CI run passed. The environment is ready for the next BullGod
development milestone, without production activation. Baseline master is
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

**Classification: RESOLVED for the known active pCloud exposure and current Git
integrity.** Actions remains CONTAINED because its historical
missing-event cause is unknown. The reviewer recommends normal integration.

The owner's conditional merge authorization was used after the independent review
and evidence publication. PR #2 was marked ready and merged through the normal
GitHub API with the expected head SHA; no check was bypassed.

## Integration and postflight

- [PR #2](https://github.com/hottweelz/CowAgent/pull/2) merged as
  [`323fefcd49bae71bbf3c191e23cf7aaca48ecb21`](https://github.com/hottweelz/CowAgent/commit/323fefcd49bae71bbf3c191e23cf7aaca48ecb21).
  Its tree exactly matches reviewed head `7be6edade3569d46f297dda23b514678ac69565d`.
- Local master was advanced through a normal, non-forced fetch of that exact
  published commit while the feature branch was checked out, then switched to
  master. Ancestry and tree equality were checked first. This avoided temporarily
  reverting the live checkout to the old baseline.
- `HEAD`, `master` and `origin/master` matched the merge SHA at 0 ahead / 0 behind.
  The feature branch remains preserved and synchronized.
- The [postflight receipt](backup-removal-postflight.json) records a second
  45-second monitor. It observed exactly the expected tracking-master update,
  local-master update and HEAD branch switch, with no unexpected change or
  invalid ref. Object integrity, worktree and preserved-file checks pass again.
- [Runtime after merge](backup-removal-runtime-after.json) matches the before
  snapshot except capture time and transient process status. Original PID/start
  time, health, data directory, all agent/config hashes, workspace/database/core
  file metadata and provider state are unchanged.
- Master automatically triggered [Tests run 42540144872](https://github.com/hottweelz/CowAgent/actions/runs/42540144872)
  at the merge SHA and passed all five jobs. The [master receipt](backup-removal-master-hosted.json)
  records logs and JUnit artifacts: macOS 5,917/39; each Linux 5,910/46; 93 passing
  subtests each; 44 JavaScript tests; strict TypeScript/build and Ruff. All log,
  ZIP and XML hashes reconcile. Exact named-case identities and skip sets match
  the prior gate. This was an automatic integration run; no native model task ran.

No checkout or metadata relocation, worktree recreation, service restart,
private-memory inspection, provider/profile change, history rewrite or production
BullGod activation occurred. The historical Git writer remains unknown.


## Remaining limits and final answers

1. **Outside pCloud coverage:** yes, for every currently configured Backup and
   Sync root, including canonical parent/child overlap checks. This does not claim
   the absence of every OS-level watch or unidentified future writer.
2. **Git and worktrees:** integrity, synchronization, monitored transitions,
   existing worktree and preserved-file checks pass.
3. **Historical cause:** still unknown. The removed exposure is a verified risk
   relationship, not proof that pCloud performed each historical conflicting write.
4. **PR #2:** normal merge completed after independent review; no bypass or history
   rewrite. Operational postflight and automatic master hosted validation passed.
5. **BullGod readiness:** yes, for capability-discovery and task-selection
   development. Production activation remains unauthorized.

Ordinary CI still excludes 15 browser integration cases and full Windows
coverage; the separate Windows Bash run remains limited evidence. Existing
warnings, floating Python dependency/action versions and Python-level network
instrumentation limits remain documented in the original report. Prior native
acceptance is not replayed or reissued for this source. The running process was
preserved; this task does not claim a service reload onto the new checkout.


The final documentation-only closeout uses `[skip ci]` and retains all eleven
implementation fingerprints from the successful merge run. No additional CI
pass is claimed for that record-only commit. The final published master commit
and 0 ahead / 0 behind check are reported in the completion handoff and PR record.
