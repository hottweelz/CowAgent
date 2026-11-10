# UPSTREAM-SELECTIVE-001 implementation plan

Baseline: accepted fork master 74b75f97e933d36e7b1b0a80b8d20afe16cbf8b2
(PRs 9–12 merged). Upstream: 6b7f5a76 (full SHA in final report). Work in
codex/upstream-selective-001 in a separate managed worktree. Preserve original
checkout, untracked files, historical branches and service on 9899.

1. Lead: port cloud identity fixes f15ba96b and 168178bf with upstream tests and
   disposable default/testpilot/testpilot2 checks. Confirm registry-unavailable,
   unknown identity and failed service construction never use another identity.
2. Luna: inspect and port shared configuration lock 4b3ea15c; deterministic
   provider/model/general/channel/nested field preservation checks.
3. Luna: inspect shared-address guard cfbc31ff then dependent Feishu guard
   5ae2c2b7. Preserve approved-reader policy and localhost opt-in.
4. Luna: inspect/port Gemini 6ca21f12 and LinkAI f6e824f9; focused timeout,
   stream and history-budget tests with no provider calls.
5. Terra 6.1: inspect MCP 25406f0e; bounded transport lifetime, fallback,
   reconnect, cancellation and cleanup need joint multi-module reasoning.
   Port only if compatible with existing worker authorization boundaries.
6. Luna: assess practical candidates 9–12, including later TLS corrections.
   Recommend minimal useful imports or explicit deferrals. Lead integrates
   only justified changes; split branches if review size warrants it.
7. Lead: review resulting diff and run complete guarded directory-mode suite
   through scripts/ci_test.py using existing virtual environment and prepared
   tokenizer cache. Run relevant JS checks and desktop build/typecheck if changed.
   One independent engineering review, resolve concrete findings, retain exact
   source/test hashes and qualified results. No accepted live-model replay.
8. Lead: candidate matrix, compatibility/dependency report and handoff; commit,
   push same-name fork branch and open draft PR(s) against verified baseline.
   Inspect hosted status once without restarting the CI control-plane inquiry.

No wholesale upstream merge, production data/credentials/approval/mount changes,
local model installation, service restart, unrelated feature work or PR merge.
