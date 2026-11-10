# UPSTREAM-SELECTIVE-001

Select useful upstream repairs without changing BullGod's personal-agent scope.
No wholesale merge, provider/credential reconfiguration, local model installation,
production data/approval/APFS changes, service restart or automatic PR merge.

## Baseline and dependencies

Accepted fork baseline: `74b75f97e933d36e7b1b0a80b8d20afe16cbf8b2`, the verified
merge of PERSONAL-004 PR12. PERSONAL-001/002/003 PR9/10/11 are ancestors.
The baseline ledger still said PR12 was draft; fetched GitHub merge metadata and
Git ancestry supersede that stale text. Latest reviewed tree matches the merge.
[Exact baseline receipt](baseline.json) records the merge SHAs, upstream head
`6b7f5a7663fe213fbeffe8075764e6f2d2d9236d`, common ancestor and current counts:
65 fork-only and33 upstream-only commits. No personal milestone remains a merge
dependency. Original personal/maintenance branches and seven untracked files
remain untouched. Git connectivity check passed; dangling recovery objects remain.

Candidate2 depends on1; candidate5 depends on4. Backend repairs form the main
branch. Desktop changes are a separate review unit, stacked above it for a final
combined-source regression. Merge backend first, then desktop after review.

## Candidate decisions

All12 defects/opportunities are present in the accepted baseline. None is already
fixed locally. Source/PR inspection was used for confirmation; local deterministic
reproduction was also obtained for the configuration overwrite. No new platform,
CLI, Docker, guest-page or search-provider feature was imported.

| Candidate | Exact upstream source | Original PR | Defect locally? | Action | Result | Conflict risk | Focused tests | BullGod compatibility |
|---|---|---|---|---|---|---|---|---|
| 1. Cloud construction isolation | [f15ba96be2d38ebb9ae0ac02aebe3bac4fd43b79](https://github.com/zhayujie/CowAgent/commit/f15ba96be2d38ebb9ae0ac02aebe3bac4fd43b79) | [# 3914](https://github.com/zhayujie/CowAgent/pull/3914) | Yes | Ported | Named service build failure returns500; no default-service dispatch. | Low | 13 upstream cases; cloud total43 plus33 three-agent cases. | Final combined regression pending; retained native evidence is separate |
| 2. Registry failure isolation | [168178bf3eb2c4933d40d0094c4b9f4d5ecde89f](https://github.com/zhayujie/CowAgent/commit/168178bf3eb2c4933d40d0094c4b9f4d5ecde89f) | [# 3921](https://github.com/zhayujie/CowAgent/pull/3921) | Yes | Ported | Registry unavailable stays distinct from absent identity and unknown404; history fails before store lookup. | Low | 22 upstream cases; cloud total43 plus33 three-agent cases. | Final combined regression pending; retained native evidence is separate |
| 3. Configuration write lock | [4b3ea15ccf249c9017f15a2bb023884d81f845f6](https://github.com/zhayujie/CowAgent/commit/4b3ea15ccf249c9017f15a2bb023884d81f845f6) | [# 3911](https://github.com/zhayujie/CowAgent/pull/3911) | Yes | Ported | Models writes share the existing settings lock; discovery stays outside it. | Low | 13 passed; deterministic provider/settings/channel/nested-field overlap. | Final combined regression pending; retained native evidence is separate |
| 4. Shared-address SSRF | [cfbc31ff283d783026c79550cf5fdc06bae7694b](https://github.com/zhayujie/CowAgent/commit/cfbc31ff283d783026c79550cf5fdc06bae7694b) | [# 3913](https://github.com/zhayujie/CowAgent/pull/3913) | Yes | Ported | Non-global IPs including100.64/10 are blocked when shared guard applies. | Low | 8 upstream cases; integrated guard/Feishu suite47 passed. | Final combined regression pending; retained native evidence is separate |
| 5. Feishu image SSRF | [5ae2c2b7ef8d3d1cb97c5eef6487e4ca7ccf60df](https://github.com/zhayujie/CowAgent/commit/5ae2c2b7ef8d3d1cb97c5eef6487e4ca7ccf60df) | [# 3916](https://github.com/zhayujie/CowAgent/pull/3916) | Yes | Ported | Shared guard runs in strict context even when global SSRF setting is off. | Low | 19 exact upstream cases passed; integrated guard/Feishu suite47 passed. | Final combined regression pending; retained native evidence is separate |
| 6. Gemini keepalive timeout | [6ca21f1268f1185bc3b43cf6d3258ed243622a37](https://github.com/zhayujie/CowAgent/commit/6ca21f1268f1185bc3b43cf6d3258ed243622a37) | [# 3912](https://github.com/zhayujie/CowAgent/pull/3912) | Yes | Ported | Comment-only streams yield for cancellation and time out after180s with monotonic clock. | Low | 9 cases; combined provider21 passed. | Final combined regression pending; retained native evidence is separate |
| 7. LinkAI history budget | [f6e824f9d30a0ffead3704846dbf270609146af3](https://github.com/zhayujie/CowAgent/commit/f6e824f9d30a0ffead3704846dbf270609146af3) | [# 3922](https://github.com/zhayujie/CowAgent/pull/3922) | Yes | Ported | Repeated old-turn removal retains system and current turn; locally corrected unusual-role deletion in upstream. | Low | 12 passed, including over-budget current-turn controls; combined provider21 passed. | Final combined regression pending; retained native evidence is separate |
| 8. MCP legacy SSE | [25406f0eb356ec19d1f2d8767952bb471bd8ae5f](https://github.com/zhayujie/CowAgent/commit/25406f0eb356ec19d1f2d8767952bb471bd8ae5f) | No separate PR identified | Yes | Ported | Persistent reader, HTTP fallback, headers, bounded next-request reconnect and errors; local origin/redirect/shutdown/deadline fixes. | Medium | Initial MCP142; final affected26 passed after review corrections. Final suite below. | Final combined regression pending; retained native evidence is separate |
| 9. Desktop streaming | [b6cff3e2dc7b655b6dfbcf8bd75cca41b9507f0a](https://github.com/zhayujie/CowAgent/commit/b6cff3e2dc7b655b6dfbcf8bd75cca41b9507f0a) | [# 3920](https://github.com/zhayujie/CowAgent/pull/3920) | Yes | Ported on desktop branch | Batch reasoning/progress and memoize bubbles with language/agent subscriptions. | Low | Pending desktop final report. | Final combined regression pending; retained native evidence is separate |
| 10. Desktop window recovery | [aa917a4a4e8b5d76e14dbb869e0b490959c0665d](https://github.com/zhayujie/CowAgent/commit/aa917a4a4e8b5d76e14dbb869e0b490959c0665d) | [# 3919](https://github.com/zhayujie/CowAgent/pull/3919) | Yes | Ported on desktop branch | Validate display geometry and recover windows after display changes. | Low | Pending desktop final report. | Final combined regression pending; retained native evidence is separate |
| 11. Public-copy deduplication | [9462cd8500bda0bc72fe39d088da2d7530285d32](https://github.com/zhayujie/CowAgent/commit/9462cd8500bda0bc72fe39d088da2d7530285d32) | No separate PR identified | Yes | Deferred | No change: source hash/copy race, size-only destination trust and mutable in-place links need separate design. | Medium | Source review only; no acceptance claimed. | Unchanged; not exercised |
| 12. Feishu WebSocket retry | [641365597131807432560ace482727c4a15e92fd](https://github.com/zhayujie/CowAgent/commit/641365597131807432560ace482727c4a15e92fd) | [# 3910](https://github.com/zhayujie/CowAgent/pull/3910) | Yes | Deferred; unsafe TLS behavior rejected | No change: final ea74daee7ebc950ac5c2c15430c9e8b66271eee4 still changes process-wide TLS verification. | High | Source/PR review only; no acceptance claimed. | Unchanged; not exercised |

## Patch and evidence

The actual application/test patches are the branch diff against the baseline;
upstream commits are selectively ported, not ancestry-merged. Candidate notes:
[cloud](isolation.md), [config](config.md), [security](security.md),
[providers](providers.md), [MCP](mcp.md), [practical assessment](practical-assessment.md).
[Plan](plan.md) defines ownership and checks. [Compatibility map](compatibility.md)
links every personal-agent gate to existing regression tests and retained native
Luna Pooler/news/specialist acceptance. Source/test hashes and final regression,
review and publication receipts will be added after the final source freeze.

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
refused. Gemini's180s cap is specifically for comment-only stretches; malformed
non-comment lines reset it, matching upstream's defined scope. Oversized LinkAI
current turns intentionally stay intact and can remain above the configured cap.
Hosted checks must be reported from observed status, never inferred from absence.

## Publication and next step

Pending final review, combined regression, branch publication and draft PR links.
Do not merge or deploy from this report while those fields are pending.
