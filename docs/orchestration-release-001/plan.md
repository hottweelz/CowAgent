# ORCHESTRATION-RELEASE-001 integrated release plan

Objective: consolidate ISOLATION-001, RECOVERY-001 and VERIFICATION-001 into a
reproducible release candidate. All requirements in the supplied release brief
remain in scope. No production data/config changes, self-evolution, deployment,
restart, unrelated features or master merge.

## Baseline and integration

- Current fork master: c2c39a2e0823f1556ecdc79f9e07911fff207a05.
- Actual ancestry is linear: master -> audit 06e0a4dd -> isolation 5b0bb0be ->
  recovery 8ed52509 -> verification 88151dff -> tracking preference b8b4b40b.
- All three implementation branches and master matched origin at start (0/0).
  Their published GitHub milestone guides were read through the GitHub connector.
- Created release/orchestration-release-001 from origin/master, then integrated
  feat/verification-001-task-outcomes by fast-forward. No cherry-picks or conflict
  resolution were required. Master stays unchanged.

## Work and owners

1. Lead: ancestry/publication receipts, requirement-to-evidence mapping,
   combined crash/restart/verification and persistent-state checks, focused fixes
   only for demonstrated blockers, integration report and Git publication.
2. Luna/high: all 16 native tool contract coverage and restricted-mode
   compatibility; identify any gap before testing. Own only its assigned
   contract tests/receipt after agreement with lead.
3. Luna/high: applicable Node/UI tests, desktop build and strict renderer
   typecheck with retained logs. No frontend fixes or weakened checks.
4. One Sol 6.1/high reviewer: integrated security/recovery/evidence boundaries;
   consequential cross-component data integrity warrants stronger reasoning
   than routine Luna review. No recursive review chain.
5. Terra 6.1/high: bounded combined process-test implementation; then a separate
   Terra 6.1/high worker fixes the two demonstrated review blockers in runtime,
   task store, runner and bridge. Cross-process state and identity integration
   require more than routine Luna edits. Lead retains persistence tests and
   integration. Effective worker models are not independently exposed.

## Gates and authoritative evidence

| Requirement | Evidence to obtain |
| --- | --- |
| Publish/reconcile/ancestry | Fetched branch SHAs, merge-base/parent chain, published docs, final upstream 0/0. |
| Restricted authority and concurrency | Existing native isolation cases plus real shared-journal claims; outside/sibling/native unsupported operations denied. |
| Immutable task inputs and persistence | Persisted envelope hashes and DB rows before/after process death/retry, frozen contract checks. |
| Safe recovery and uncertain effects | Kill owned fixture before model/tool execution, after intent, after real write/before receipt, after completion; restart real consumer. |
| Cancellation/timeout/revocation | Durable stop provenance, late returns fenced, current grants revoked before retry, no unauthorized effect. |
| Independent verification | Recovery followed by artifact readback, wrong/missing artifacts fail, completed work never replays after verification failure. |
| Persistent identity/memory/history | Synthetic profiles, instruction/memory files and conversation rows preserved across execution/restarts; real FTS retrieval with LIKE fallback blocked. |
| WAL/journal health | Journal and memory integrity/foreign-key checks, WAL mode, FTS MATCH, read/reopen repetition. |
| Regression | Complete retained SQLite/EFFICIENCY/ISOLATION/RECOVERY/VERIFICATION/native orchestration selection plus integration cases. |
| Native tool compatibility | All 16 current descriptors/contracts checked; intentional restricted denials documented separately from privileged owner contracts. |
| UI/build/static | Applicable Node tests, desktop npm build, strict renderer tsc, Python F-class lint and compilation. |
| Review/release report | One independent review, fix blockers with regressions, publish README and evidence with exact SHAs and limitations. |

The nine pre-existing ChannelsPage TS2322 errors remain a failed gate. A passing
desktop build cannot replace strict typecheck. Final decision must report every
failed gate and remediation; no merge occurs while a required gate fails.

Use isolated HOME/COW_DATA_DIR and fictional workspaces only. Reuse valid
execution receipts where coverage is sufficient; add only missing combined
scenarios. Final checks must prove DB state and observed effects, not worker prose.
