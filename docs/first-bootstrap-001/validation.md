# Baseline and evidence reconciliation

## Finding

PR #5 remains open and draft. Its current head is `8d182026be2380fc574eeecd13edcffa5ed1dcb1`, based on PR #4 at `a507a400985512683c870ef4fe059fa5982ad13e`. PR #4 is also open and draft, based on current `master` at `f659349785acf98905901a5cc53921436a109dbc`. All three heads are in the PR #5 ancestry. The PR metadata was checked with the GitHub read-only connector; the parent independently checked the current heads during this task.

The executable candidate is commit `005c1e4805c75017467b817baa2a8bbbe3f7511d`, tree `d9d8c64ef453e4e44860e2516c070258b1957b1d`. PR #4 documentation head a507a400 precedes the PR #5 executable commit. The later PR #5 head adds docs, `MEMORY.md`, and `CHANGELOG_AI.md`; no runtime file changes after the candidate appear in the local comparison. The hosted PR #5 merge tree equals the candidate tree. The 368-file source manifest recorded by the real owned-process rehearsal is bound to that same candidate. This supports carrying the executable results forward to the current documentation head. It does not show that hosted CI ran on the docs-only head.

## Evidence that can be carried forward

- Full local protected regression on source `005c1e48`: 6,124 passed, 36 skipped, 93 passing subtests, zero failures/errors. Receipt: `docs/bullgod-discovery-002/service-drain-local.json`; private receipt SHA-256 matches the recorded hash.
- Hosted run `42699928448`, attempt 1, ran on PR #5 source `005c1e48` and completed successfully with no reruns. Linux Python 3.11, Linux Python 3.13, macOS Python 3.13, JavaScript tests, strict TypeScript/build, and Ruff all passed. Receipt: `docs/bullgod-discovery-002/service-drain-hosted.json`; retained private receipt hash matches.
- Hosted comparison reconciled 6,160 case identities across the three Python platforms, with 45 new identities, none removed, and unchanged platform skip identities versus the accepted PR #4 source.
- Disposable process rehearsal used the same candidate commit and reported a matching 368-file startup manifest, owner binding, close/reject/complete/drain behavior, graceful candidate exit, pinned fallback startup, health checks, and preserved fictional rows/sentinel. Receipt: `docs/bullgod-discovery-002/service-drain-rehearsal.json`.
- The latest project handoff records two independent-review findings corrected and targeted checks cleared: probes require a closed zero-work barrier with generation fencing; detached provider work sets an unsupported-coverage blocker before dispatch. GitHub currently has zero submitted review records and zero inline review threads on each PR. The project handoff is the review evidence.

No new full runtime suite is needed solely to reconcile documentation-only commits; this milestone separately tests its new fictional bootstrap and recovery fixtures. Re-run affected validation only if executable source, runner workflow, dependency inputs, or the source manifest changes.

## Git and preservation evidence

The current working branch began at `8d182026` with tracked files clean and a single untracked `AGENTS.md`. The parent then fetched without prune and confirmed `origin/codex/bullgod-service-drain` at `8d182026` and `origin/master` at `f6593497`; the tracked source branch was 0 ahead / 0 behind. After that check, the source-to-head diff remained seven documentation, `MEMORY.md`, and `CHANGELOG_AI.md` paths. The original primary checkout's seven pre-existing untracked paths still exist and match each recorded SHA-256 from `docs/infra-reliability-001/baseline.json`. The five preserved recovery artifacts also exist and match their recorded SHA-256 values; the recovery manifest itself matches its recorded hash. This was metadata/hash verification only.

The shared repository includes origin and upstream remotes and many worktrees. A read-only `git fsck` reported unreachable objects. No fetch, prune, garbage collection, reset, ref update, or cleanup was performed. Keep the preserved artifacts and follow `docs/infra-reliability-001/recovery.md` if reconciliation is needed.

## Limits for bootstrap qualification

These results qualify PR #5's code and its disposable process mechanics. They do not establish old-process quiescence, current live work state, durable live-data backup/recovery, or the original process's loaded source. The test controller was a private parent-owned stdin pipe, not an operator endpoint shipped in CowAgent. Existing unsupported ingress/effects remain blockers for a positive drain receipt. The independently reviewed maintenance effects and legacy-process uncertainty remain separate gates. Phase 1 and Phase 8 evidence alone cannot issue a GO decision.

## Checks performed

- Read current GitHub PR #4/#5 metadata, PR review submissions and inline thread state, and workflow runs for tested source.
- Checked local branch/worktree/remote metadata, ancestry, commit trees, and the file list between tested source and PR #5 head.
- Compared retained hosted/local receipt hashes with their private counterparts.
- Checked recovery manifest and five artifact hashes; checked seven original untracked paths by existence and hash.
- Read existing source, CI, rehearsal and handoff evidence. No test, service, model, adapter, or signal command was run.
