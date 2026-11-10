# UPSTREAM-SELECTIVE-001

Select useful upstream repairs without changing BullGod's personal-agent scope.
No wholesale merge, provider/credential reconfiguration, local model installation,
production data/approval/APFS changes, service restart or automatic PR merge.

## Baseline and dependencies

Accepted fork baseline: `74b75f97e933d36e7b1b0a80b8d20afe16cbf8b2`, the verified
merge of PERSONAL-004 PR #12. PERSONAL-001/002/003 PRs #9, #10 and #11 are ancestors.
The baseline ledger still said PR #12 was draft; fetched GitHub merge metadata and
Git ancestry supersede that stale text. Latest reviewed tree matches the merge.
[Exact baseline receipt](baseline.json) records the merge SHAs, upstream head
`6b7f5a7663fe213fbeffe8075764e6f2d2d9236d`, common ancestor and current counts:
65 fork-only and 33 upstream-only commits. No personal milestone remains a merge
dependency. Original personal/maintenance branches and seven untracked files
remain untouched. Git connectivity check passed; dangling recovery objects remain.

Candidate 2 depends on 1; candidate 5 depends on 4. Backend repairs form the main
branch. Desktop changes are a separate review unit, stacked above it for a final
combined-source regression. Merge backend first, then desktop after review.

## Candidate decisions

All 12 defects/opportunities are present in the accepted baseline. None is already
fixed locally. Source/PR inspection was used for confirmation; local deterministic
reproduction was also obtained for the configuration overwrite. No new platform,
CLI, Docker, guest-page or search-provider feature was imported.

| Candidate | Exact upstream source | Original PR | Defect locally? | Action | Result | Conflict risk | Focused tests | BullGod compatibility |
|---|---|---|---|---|---|---|---|---|
| 1. Cloud construction isolation | [f15ba96be2d38ebb9ae0ac02aebe3bac4fd43b79](https://github.com/zhayujie/CowAgent/commit/f15ba96be2d38ebb9ae0ac02aebe3bac4fd43b79) | [# 3914](https://github.com/zhayujie/CowAgent/pull/3914) | Yes | Ported | Named service build failure returns 500; no default-service dispatch. | Low | 13 upstream cases; cloud total 43 plus 33 three-agent cases. | Verified by combined local regression; live evidence retained separately |
| 2. Registry failure isolation | [168178bf3eb2c4933d40d0094c4b9f4d5ecde89f](https://github.com/zhayujie/CowAgent/commit/168178bf3eb2c4933d40d0094c4b9f4d5ecde89f) | [# 3921](https://github.com/zhayujie/CowAgent/pull/3921) | Yes | Ported | Registry unavailable stays distinct from absent identity and unknown 404; history fails before store lookup. | Low | 22 upstream cases; cloud total 43 plus 33 three-agent cases. | Verified by combined local regression; live evidence retained separately |
| 3. Configuration write lock | [4b3ea15ccf249c9017f15a2bb023884d81f845f6](https://github.com/zhayujie/CowAgent/commit/4b3ea15ccf249c9017f15a2bb023884d81f845f6) | [# 3911](https://github.com/zhayujie/CowAgent/pull/3911) | Yes | Ported | Models writes share the existing settings lock; discovery stays outside it. | Low | 13 passed; deterministic provider/settings/channel/nested-field overlap. | Verified by combined local regression; live evidence retained separately |
| 4. Shared-address SSRF | [cfbc31ff283d783026c79550cf5fdc06bae7694b](https://github.com/zhayujie/CowAgent/commit/cfbc31ff283d783026c79550cf5fdc06bae7694b) | [# 3913](https://github.com/zhayujie/CowAgent/pull/3913) | Yes | Ported | Non-global IPs including 100.64/10 are blocked when shared guard applies. | Low | 8 upstream cases; integrated guard/Feishu suite 47 passed. | Verified by combined local regression; live evidence retained separately |
| 5. Feishu image SSRF | [5ae2c2b7ef8d3d1cb97c5eef6487e4ca7ccf60df](https://github.com/zhayujie/CowAgent/commit/5ae2c2b7ef8d3d1cb97c5eef6487e4ca7ccf60df) | [# 3916](https://github.com/zhayujie/CowAgent/pull/3916) | Yes | Ported | Shared guard runs in strict context even when global SSRF setting is off. | Low | 19 exact upstream cases passed; integrated guard/Feishu suite 47 passed. | Verified by combined local regression; live evidence retained separately |
| 6. Gemini keepalive timeout | [6ca21f1268f1185bc3b43cf6d3258ed243622a37](https://github.com/zhayujie/CowAgent/commit/6ca21f1268f1185bc3b43cf6d3258ed243622a37) | [# 3912](https://github.com/zhayujie/CowAgent/pull/3912) | Yes | Ported | Comment-only streams yield for cancellation and time out after 180 s with monotonic clock. | Low | 9 cases; combined provider 21 passed. | Verified by combined local regression; live evidence retained separately |
| 7. LinkAI history budget | [f6e824f9d30a0ffead3704846dbf270609146af3](https://github.com/zhayujie/CowAgent/commit/f6e824f9d30a0ffead3704846dbf270609146af3) | [# 3922](https://github.com/zhayujie/CowAgent/pull/3922) | Yes | Ported | Repeated old-turn removal retains system and current turn; locally corrected unusual-role deletion in upstream. | Low | 12 passed, including over-budget current-turn controls; combined provider 21 passed. | Verified by combined local regression; live evidence retained separately |
| 8. MCP legacy SSE | [25406f0eb356ec19d1f2d8767952bb471bd8ae5f](https://github.com/zhayujie/CowAgent/commit/25406f0eb356ec19d1f2d8767952bb471bd8ae5f) | No separate PR identified | Yes | Ported | Persistent reader, HTTP fallback, headers, bounded next-request reconnect and errors; local origin/redirect/shutdown/deadline fixes. | Medium | Initial MCP 142; final affected 26 passed after review corrections. Final suite below. | Verified by combined local regression; live evidence retained separately |
| 9. Desktop streaming | [b6cff3e2dc7b655b6dfbcf8bd75cca41b9507f0a](https://github.com/zhayujie/CowAgent/commit/b6cff3e2dc7b655b6dfbcf8bd75cca41b9507f0a) | [# 3920](https://github.com/zhayujie/CowAgent/pull/3920) | Yes | Ported on desktop branch | Batch reasoning/progress and memoize bubbles with language/agent subscriptions. | Low | 16 desktop tests passed; renderer/main build and strict typecheck passed. | Verified by combined local regression; live evidence retained separately |
| 10. Desktop window recovery | [aa917a4a4e8b5d76e14dbb869e0b490959c0665d](https://github.com/zhayujie/CowAgent/commit/aa917a4a4e8b5d76e14dbb869e0b490959c0665d) | [# 3919](https://github.com/zhayujie/CowAgent/pull/3919) | Yes | Ported on desktop branch | Validate display geometry and recover windows after display changes. | Low | 16 desktop tests passed; renderer/main build and strict typecheck passed. | Verified by combined local regression; live evidence retained separately |
| 11. Public-copy deduplication | [9462cd8500bda0bc72fe39d088da2d7530285d32](https://github.com/zhayujie/CowAgent/commit/9462cd8500bda0bc72fe39d088da2d7530285d32) | No separate PR identified | Yes | Deferred | No change: source hash/copy race, size-only destination trust and mutable in-place links need separate design. | Medium | Source review only; no acceptance claimed. | Unchanged; not exercised |
| 12. Feishu WebSocket retry | [641365597131807432560ace482727c4a15e92fd](https://github.com/zhayujie/CowAgent/commit/641365597131807432560ace482727c4a15e92fd) | [# 3910](https://github.com/zhayujie/CowAgent/pull/3910) | Yes | Deferred; unsafe TLS behavior rejected | No change: final ea74daee7ebc950ac5c2c15430c9e8b66271eee4 still changes process-wide TLS verification. | High | Source/PR review only; no acceptance claimed. | Unchanged; not exercised |

## Patch and evidence

The actual application/test patches are the branch diff against the baseline;
upstream commits are selectively ported, not ancestry-merged. Candidate notes:
[cloud](isolation.md), [config](config.md), [security](security.md),
[providers](providers.md), [MCP](mcp.md), [desktop](desktop-validation.md),
[practical assessment](practical-assessment.md).
[Plan](plan.md) defines ownership and checks. [Compatibility map](compatibility.md)
links every personal-agent gate to existing regression tests and retained native
Luna Pooler/news/specialist acceptance. [Backend source/test hashes](source-hashes.json) identify the exact patch bytes.
[Independent review](review.md) has no open source finding. The [complete combined regression](regression.md) passed **6,360 tests and
93 subtests**, with 36 skips, zero failures/errors, in 220.85 s.
[Combined source/test hashes and result](combined-validation.json) were unchanged
before/after the run. Web JavaScript: 39 and desktop: 16 checks, commitmentsUI, strict
renderer typecheck, renderer/main builds and project RuffF gate passed.
Independent review has no unresolved source finding.

The suite emitted 36 warnings, including an unraisable WebSocket Bad-file-descriptor
warning; it did not fail a test. Attribution was not established and no unrelated
WebSocket cleanup change was made. Existing optional-font, Browserslist, mixed-import
and bundle-size build warnings remain. See the regression receipt for details.

## Deliberately deferred

- Public-copy deduplication: keep existing behavior until content actually copied
  can be authenticated and published-link snapshot semantics are settled.
- Feishu reconnect: reject broad TLS disabling, including the later upstream
  correction. A separate per-client verified-TLS retry design is required.
  The pre-existing baseline certificate fallback is not fixed by this task.
- SpecStream search, guest-page controls, Docker expansion, unrelated CLI options,
  cosmetic documentation and unused integrations remain potential future work.
  No compelling personal-agent requirement was found to widen this milestone.

## Limits

Local fixture success does not certify current provider availability, live news,
production state, third-party MCP servers or physical multi-monitor behavior.
The accepted real GPT-6 Luna Pooler/specialist evidence remains historical and
was not replayed. No routing settings changed; GPT-5.6 manual fallback remains.
MCP shutdown releases stream waiters but cannot forcibly interrupt every blocking
POST/DNS operation. Cross-origin legacy endpoints and authenticated redirects are
refused. Gemini's180 s cap is specifically for comment-only stretches; malformed
non-comment lines reset it, matching upstream's defined scope. Oversized LinkAI
current turns intentionally stay intact and can remain above the configured cap.
Hosted checks must be reported from observed status, never inferred from absence.

## Publication and next step

[Draft PR #13: backend repairs](https://github.com/hottweelz/CowAgent/pull/13), then
[draft PR #14: desktop fixes](https://github.com/hottweelz/CowAgent/pull/14). Both
remain unmerged. See [publication and hosted status](publication.md). Hosted
checks/statuses are empty, so hosted validation remains unverified. Source/test
hashes are unchanged; both tracked branches are synchronized after final push.
The worktrees retain only untracked AGENTS.md copies. Review13 before14;
deployment remains separate.
