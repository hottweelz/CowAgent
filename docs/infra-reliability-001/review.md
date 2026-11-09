# Independent engineering review

One Sol6.1/high reviewer performed the independent review. The task required
cross-component reasoning about Git data integrity, linked worktrees, rollback,
CI secrets/permissions and evidence claims. Requested model selection was explicit;
the runtime does not independently expose the effective model identity.

Scope: baseline fe00855a through final source c03d35e6, plus this report and
recovery/migration documents. The reviewer operated read-only, used no nested
reviewers, ran no model acceptance or full regression, and changed no repository,
service, provider or private-memory state.

## Findings resolved

- Declare tiktoken explicitly for the public cache-preparation step. The hosted
  environment happened to contain it transitively; that was not a maintainable
  prerequisite. scripts/requirements-ci.txt now declares the existing spec.
- Remove an unused variable observed during watcher editing, before publication.
- The lead also required the watcher to latch observed invalid-ref failure even
  after a conflict copy disappears. The focused integration test proves this.

No actionable source finding remains in the reviewed implementation. The reviewer
checked the timeout recovery/result/UI path, preservation of specific errors,
Linux missing/zombie/reaped states and live-process rejection, real Unix listener
readiness, least-privilege workflow tokens, credential-free checkout, environment
isolation and changed-file lint input handling.

The final narrow update adds only missing hosted prerequisites and exact ESRCH
handling. Browser/model integration remains outside ordinary hosted tests. The
Python socket guard is not subprocess/native network confinement.

All eleven implementation hashes in validated-source.json were independently
compared with both current files and commit c03d35e6 and matched.

## Git and evidence review

The pCloud Backup relationship is direct UI evidence. The historical ref writer
and missing automatic Actions event cause remain untraced; no permanent root-cause
resolution is claimed. The failed migration rehearsal correctly blocks live
execution. Polling/fetch success is not isolation or proof that the writer is gone.

Recovery instructions preserve the full metadata, worktrees, dirty/untracked
content, conflict artifacts and newer commits before rollback. Expected-old ref
updates prevent silently overwriting a concurrent ref change. The main and linked
worktree topology, pointer exposure and failed rollback remain explicit limits.

Git classification is BLOCKED. The current checkout is not sufficiently reliable
to begin the next BullGod milestone while active Backup includes its metadata.

## Hosted evidence review

Final receipt reconciliation passed with no actionable finding. The reviewer
checked retained GitHub API results, logs, artifact metadata and local ZIP/XML
bytes independently, without another hosted run or fresh API request:

- Run 42536883493 binds to source c03d35e6. All five checkout logs identify the
  merge of that head into baseline fe00855a; all five jobs completed successfully.
- All five log hashes match. Each of the three ZIP hashes matches both the
  receipt and retained GitHub artifact index. XML digests and ZIP members match.
- Reparsed JUnit has 5,956 named cases and 6,049 entries including 93 subtests per
  Python job, with zero failures/errors. macOS has 5,917 passed and 39 skipped;
  each Linux job has 5,910 passed and 46 skipped. Exact skip dictionaries and
  pytest log summaries match. The source contains 708 tracked Python test files.
- JavaScript logs confirm 39 web and 5 desktop tests passed with zero failures.
  Strict TypeScript, renderer/main build and changed-file Ruff checks passed.

The successful Windows run covers only its Bash streaming file (11 passed,
5 skipped), not all Windows behavior. The 15 browser integration cases and
platform-specific skips remain outside this ordinary gate. Earlier failed matrix
receipts remain retained and excluded from passing evidence.

Final assessments are supported: **Git BLOCKED; Actions CONTAINED; BullGod
readiness No.** The historical writer and missing-dispatch causes remain unproven.
See [hosted-final.json](hosted-final.json) and
[validated-source.json](validated-source.json). A later documentation-only commit
does not change the implementation covered by this review or claim a new CI run.
