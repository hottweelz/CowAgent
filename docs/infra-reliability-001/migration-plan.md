# Git metadata migration plan (approval draft)

## Status

**Do not execute on the live checkout.** The disposable rehearsal found that
`git init --separate-git-dir` with an existing detached linked worktree leaves
`git worktree list` pointing the primary worktree at the external metadata path.
`git worktree repair` reports an unreadable gitdir file. Setting `core.worktree`
to the unchanged checkout path did not fix it. See
[migration-rehearsal.json](migration-rehearsal.json).

The candidate metadata path is:

`/Users/jamestylee/Library/Application Support/CowAgentGit/CowAgent.git`

The parent reports that the pCloud UI showed this path outside both active
backup roots and that the path does not exist. This worker did not inspect or
change pCloud. The live repository path remains under the backed-up Projects
tree. Git metadata migration requires a corrected rehearsal and separate explicit
maintainer authorization.

## Follow-up diagnosis: live migration remains blocked

Git 2.50.1 derives its main worktree listing from the common Git directory path,
stripping only a trailing `/.git`, without consulting `core.worktree`. The
[Git 2.50.1 source](https://github.com/git/git/blob/v2.50.1/worktree.c#L94-L118)
shows this calculation. A fresh disposable separate-directory fixture reproduced
the incorrect external path both before and after setting `core.worktree`. The
reported primary path is wrong even though ordinary operations may work. Do not
accept that state or run worktree repair as proof that it is safe.

A separate disposable experiment converted the common directory to bare and
registered the primary checkout as a linked worktree. It preserved the staged,
unstaged, and untracked fixture and its existing detached worktree. A local
commit, push, and fetch passed. The subsequent rollback initially failed:
`git worktree repair` encountered the primary checkout's restored `.git`
directory where the stale linked registration expected a gitfile. Moving that
registration aside in the disposable fixture allowed repair and retained the
post-move commit. This manual metadata change is not a validated live rollback.
The conversion and rollback are not approved procedures. Git remains **BLOCKED**
for live migration until a documented, fully tested procedure covers all live
worktrees and failure points. See [the rehearsal](migration-rehearsal.json).

The `.git` pointer itself would remain in a pCloud backup root. Moving its target
does not prevent pCloud from replacing or conflicting the pointer with an old
backup. A future proposal must obtain explicit approval for a verified pCloud
pause or exclusion and a metadata/pointer snapshot strategy, and must test
resume and rollback without clobbering newer commits. A transfer pause alone
is not proof of exclusion or safety after resume. No live migration is authorized.

## Required approval scope

Before live work, obtain approval for a bounded maintenance window that permits:

- Briefly pause and resume pCloud transfers only. Do not stop or disable Backup.
- Move the live `.git` directory to the verified candidate path and replace it
  with a per-machine absolute `.git` pointer.
- Run the specified Git checks and restore from the preserved metadata snapshot
  if any check fails.

This approval does not permit deletion of conflict copies, history rewriting,
force push, reset, remote changes, service restart, or changes to other files.

## Preconditions

1. Complete a successful disposable rehearsal that preserves the primary checkout
   path, all refs and objects, upstream tracking, dirty and untracked content, and
   every linked worktree. Confirm `git worktree list`, each worktree's
   `rev-parse --show-toplevel`, and `git status` before and after.
2. Confirm the destination remains outside all active pCloud backup roots and is
   not part of another sync or backup service. Confirm it is writable and has
   enough space for the full Git directory and rollback copy.
3. Confirm no Git writer is active. Record `git status --short --branch`,
   `git worktree list --porcelain`, `git remote -v`, branch/upstream, object and
   ref checks, and current checkout and linked-worktree absolute paths.
4. Preserve a complete byte-level copy of `.git` outside the backed-up tree. Do
   not alter or remove the original until the migrated repo passes every check.
   Preserve any conflict artifact as a distinct named file; do not merge or
   overwrite it.
5. Pause pCloud transfers only after the maintainer approves the maintenance
   window. Keep Backup enabled. Confirm the pause in the UI and confirm no
   transfer is active before replacing `.git`.

## Proposed migration sequence (not validated for live use)

The command below is a proposal only. The rehearsal failed its linked-worktree
acceptance gate, so do not run it until a corrected disposable sequence passes.

```sh
repo='/Volumes/Predator SSD GM7 1TB/Projects/CowAgent'
metadata='/Users/jamestylee/Library/Application Support/CowAgentGit/CowAgent.git'
```

The corrected procedure must first preserve the full existing Git directory,
then relocate metadata without changing the checkout path, then repair and verify
each linked worktree. It must not rely on `git init --separate-git-dir` alone.
The current rehearsal does not establish a safe command sequence for this state.

## Required post-move checks

Before resuming pCloud transfers, require all of these checks to pass:

- `cat "$repo/.git"` shows the approved absolute metadata path.
- `git -C "$repo" rev-parse --show-toplevel --absolute-git-dir` reports the
  unchanged checkout path and approved metadata path.
- `git -C "$repo" status --short --branch` matches the preflight dirty and
  untracked set exactly.
- `git -C "$repo" show-ref`, `git -C "$repo" branch -vv`, and
  `git -C "$repo" worktree list --porcelain` match the preflight refs, upstream,
  and worktree paths.
- For every linked worktree, `git -C <path> rev-parse --show-toplevel
  --absolute-git-dir` reports the expected worktree and shared metadata paths;
  each `.git` pointer and admin `gitdir` backpointer resolves both ways.
- `git fsck --full` completes without new errors. Compare all expected object and
  ref IDs with the preflight record.
- Create no live commit and perform no network push as part of migration
  verification. This rehearsal's push/fetch was local to a disposable bare repo.
- Confirm pCloud is still paused, no `.git` conflict copy appeared, and the
  original metadata snapshot remains byte-identical.

Only after the maintainer approves resume should pCloud transfers resume. Wait
for the client to settle. Then recheck the absolute `.git` pointer, repository
status, worktree list, metadata snapshot, and pCloud activity. A sync conflict,
wrong pointer, changed status, missing ref/object, or broken linked worktree is a
stop condition: pause transfers and use the preserved snapshot to restore the
prior metadata state. Do not delete the failed state or any conflict artifact.

## Rollback evidence and limits

The disposable rollback preserved its post-move commit and tracking ref after
moving the metadata back. Main-worktree repair alone emitted a linked-worktree
warning; repair from the detached linked worktree then restored a correct worktree
listing. This proves the disposable rollback path for that fixture only. It does
not validate migration of the live checkout or prove that pCloud is quiet during
a real transition.

The `.git` pointer contains an absolute path. It is specific to this Mac and
checkout path. Another machine or checkout needs its own pointer. Keep the Git
metadata outside pCloud and other file-sync conflict handling; do not assume a
pointer file is protected because the target metadata is excluded.
