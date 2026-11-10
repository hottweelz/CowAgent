# Initial publication and final merge status

PRs #13 and #14 were subsequently merged in order under maintainer authorization.
See [merge closeout](merge-closeout.md). The initial observations below are retained
as historical evidence and do not describe the current PR state.

Observed 2026-11-10 14:37 EST.

1. [Draft PR #13](https://github.com/hottweelz/CowAgent/pull/13):
   `codex/upstream-selective-001` into verified `master`74b75f97. Candidates1–8.
2. [Draft PR #14](https://github.com/hottweelz/CowAgent/pull/14):
   `codex/upstream-selective-001-desktop` into the backend branch. Candidates9–10.
   Review and merge #13 first; then review #14 against the integrated baseline.

Both PRs remain draft, open and unmerged. Both are attached to this chat.
Original personal-agent/maintenance branches and PRs remain unchanged.

## Hosted observation

GitHub check diagnostics for exact publication heads:

- PR13 `83d3b11c24b8755fb661dfae61c752d1a4ee636f`: checks[], statuses[], jobs[].
- PR14 `b9709abc78308cd16524fb178381777dfdf7c04a`: checks[], statuses[], jobs[].

No passing hosted execution is available. Draft publication provided the normal
PR event opportunity; no control-plane, runner, workflow configuration or CI
permissions investigation was reopened. These final handoff edits change docs
only and preserve all validated source/test hashes. Empty checks are not a pass.

## Git and preservation

Both branches were pushed with same-name origin tracking. Fetch with prune and
upstream comparison confirmed0ahead/0behind at initial publication. The final
documentation push is followed by the same sync check before task completion.
There is no source/test difference from the validated combined manifest after
stacking and publication. Worktrees are clean except intentionally untracked
AGENTS.md copies. No force push, branch removal, upstream merge or live restart.

The original checkout remains codex/bullgod-discovery-002 with the same seven
untracked recovery/instruction files. Read-only lsof still shows PID28093 on
127.0.0.1:9899. Production data, credentials, approvals and APFS ownership were
not changed. No local inference model was installed.

## Remaining limits and next action

Maintainer review of #13, then #14. Keep deployment separate. Local regression
passed; hosted checks, live providers/third-party MCP and physical display events
remain unverified. Full regression warnings and historical native evidence are
qualified in regression.md and compatibility.md. No source review finding is open.
