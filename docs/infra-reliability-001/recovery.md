# Git and Actions recovery procedures

This procedure preserves evidence. It does not authorize a live metadata move,
backup setting change, forced push, reset or deletion of conflict artifacts.
INFRA-RELIABILITY-001B verified that the owner removed Projects from Backup and
that no remaining Backup/Sync rule covers the checkout or runtime. See the
[addendum](backup-removal-verification.md). Recheck coverage if conflicts recur.

## Observe without changing Git

Run from the CowAgent checkout. Select an output path outside both the checkout
and common Git directory. The output contains ref identifiers and commit IDs,
not private configuration or reflog messages.

```sh
repo='/Volumes/Predator SSD GM7 1TB/Projects/CowAgent'
evidence=$(mktemp -d /private/tmp/cow-ref-observation.XXXXXX)
python3 scripts/git_ref_watch.py --repo "$repo" --duration 60 --interval 0.25   --output "$evidence/refs.jsonl"   --expect-ref refs/heads/master=fe00855a9f7b896115b2268492e11aa82d9bdc10   --expect-ref refs/remotes/origin/master=fe00855a9f7b896115b2268492e11aa82d9bdc10
```

The baseline SHA is valid for this report; replace it only after separately
verifying a later intentional master change. Exit 2 means a mismatching expected
ref or an observed invalid conflict ref. A failure remains latched even if the
conflict disappears. The monitor does not authorize or repair any update.
It can miss between-sample changes. A clean run does not establish safety.

To attribute a future write, an administrator can perform a bounded macOS
`fs_usage` capture while reproducing only an approved, ordinary Git operation.
The current agent cannot run that trace because sudo requires a password. Do not
share a password with an agent. Do not install a privileged daemon.

```sh
set -o pipefail
repo='/Volumes/Predator SSD GM7 1TB/Projects/CowAgent'
evidence=$(mktemp -d /private/tmp/cow-ref-attribution.XXXXXX)
sudo /usr/bin/fs_usage -w -f filesys -t 60 2>&1   | awk -v root="$repo/.git" 'index($0, root) { print }'   > "$evidence/ref-writers.txt"
```

Only path-matching lines are retained; inspect the pipeline exit status too.
This command is an operator procedure, not an executed trace or a permanent
monitor. A positive matching event identifies an observed process/PID; no event
cannot clear an intermittent writer. If metadata moves in a future approved
operation, use the then-current common Git path instead of this old path.

## Preserve before any repair

1. Stop Git writers and obtain approval before pausing/changing backup behavior.
   Record current refs, common directory, every worktree path, branch/upstream,
   staged/unstaged diffs and untracked inventory. Do not stage unrelated files.
2. Copy the complete common Git directory to a unique location outside all active
   backup roots. Preserve each linked worktree's `.git` pointer and metadata.
   Keep staged and unstaged patches separate, plus copies of untracked content.
   A Git bundle alone does not preserve the index or uncommitted work.
3. Record SHA-256 hashes of conflict copies. Validate any candidate commit with
   `git cat-file -e COMMIT^{commit}` before using it. Keep every existing recovery
   ref and backup. Do not run prune/garbage collection as a repair.
4. Compare `git ls-remote origin refs/heads/master` with the recorded accepted
   commit and the independent remote history. A local tracking ref alone is not
   proof of published state. If histories differ, stop and reconcile; do not
   force-push or reset to make counts look clean.

## Narrow ref repair, only after evidence review

The previous incident preserved generated invalid ref files outside `.git/refs`
and used expected-old `git update-ref` operations. Its remote merge was already
verified. This is not a blanket command to make local state match a remote.

For a future incident, first preserve all affected commits under new valid
recovery refs where possible. If an invalid conflict-name blocks Git enumeration,
move that exact artifact to the preserved evidence directory only after recording
its bytes/hash; never delete it. Do not move unrelated valid refs. Resolve each
ref's intended commit independently, then use `git update-ref REF NEW OLD` so a
concurrent change causes rejection. Repair the index only when its intended state
and all working content are independently preserved and compared.

Packing verified refs can avoid reliance on a damaged loose ref, but it does not
exclude `.git` from pCloud or prove the writer has stopped. Do not use packing as
a permanent sync fix. After any approved repair, require successful fetch,
correct local/remote resolution, correct upstreams, unchanged untracked content
and working linked worktrees. Keep all recovery artifacts even after success.

## Rollback and development decision

[The migration rehearsal](migration-plan.md) is not approved for live use. Its
experimental topology/rollback limitations remain. No live files were moved.
A future operator must preserve commits created after a move before rollback;
restoring only an older snapshot would discard those commits. Keep the failed
state as separate evidence and repair pointers only through a validated plan.

The migration proposal is superseded by the owner's removal of the Projects
backup. Keep the checkout and metadata in place. The addendum records current
coverage and Git integrity; follow its integration decision. If backup coverage
returns, stop normal Git writes and investigate before attempting repair. A clean
poll or fetch alone does not clear a newly detected backup exposure.

## Detect and investigate a missing Actions run

For an intended ordinary PR or master event, retain its exact head SHA and time.
Check actual runs rather than inferring execution from workflow YAML:

```sh
gh run list --repo hottweelz/CowAgent --workflow test.yml --limit 20 \
  --json databaseId,event,headSha,status,conclusion,url
```

Match the expected event and head. Record a missing run as a gate failure. Do not
equate a queued job, HTTP 204 dispatch response, or older successful SHA with a
successful run. For an actual run, replace RUN_ID below with its returned ID:

```sh
gh run view RUN_ID --repo hottweelz/CowAgent \
  --json databaseId,event,headSha,status,conclusion,jobs,url
gh run view RUN_ID --repo hottweelz/CowAgent --log
```

If no run exists, capture the workflow state, Actions policy and relevant branch,
path, event and skip filters through the official API. Do not broaden token
permissions, disable protection or assume a billing cause. The recognized
existing Windows Bash workflow supplied a verified diagnostic dispatch path:

```sh
gh workflow run test-windows-bash.yml --repo hottweelz/CowAgent --ref master
```

This executes the existing Windows Bash test, not the complete matrix. It still
requires a subsequent run ID, started job, successful conclusion and retrieved
logs. Use it only for an intended infrastructure check, not repeated polling.
The proposed Tests dispatch requires a full `base_sha` input and becomes a usable
default-branch recovery option only after explicit integration review places that
workflow definition on master. Until then, PR events are the demonstrated path
for the candidate full matrix. No branch protection was changed to enforce it.

See GitHub's [manual-run procedure](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
and [dispatch API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event).
The historical zero-run cause remains unknown. Preserve failed logs and exact
source binding before correcting a demonstrated problem. Reuse passing evidence
when only receipts change; do not replay native model acceptance for CI recovery.
