# Independent review and validation

## Review scope and resolution

One bounded independent engineering review used GPT Sol 6.1/high because the
assignment involved authority, cross-process publication, replay and durable
data integrity. Luna workers handled routine inventory, local/hosted evidence
and reconciliation; Terra 6.1 handled plugin/process integration. The lead owns
integration and publication. No recursive or external review pool was used.

The source review identified and cleared three concrete findings:

| Finding | Correction | Independent verification |
| --- | --- | --- |
| Failed plugin import or missing enabled registration could look like absence of work. | Sticky import/initialization/missing-registration blockers. | Focused failure tests, source review and full regression. |
| Generic `inspect.unwrap` accepted replaced methods carrying the old `__wrapped__` target. | Compare raw compiled methods; accept only the exact expected CowCli drain wrapper with correct target/category. | Genuine Finish passes; wrapped replacement rejects. |
| Hardlink publication exposed a two-link final name, or visible bytes before directory durability. | Separate I/O lock; each read/write owns a separate descriptor; serialize through temporary unlink and directory fsync; reader fsync before acceptance; failed publish removes final name under lock. | Deterministic separate-process and thread pause tests after link/before fsync; injected writer/reader fsync failures reject. Independent reproductions found no early accepted receipt. |

The reviewer then verified the actual process receipts, native recovery scope,
manifest, source-selection/CLI policy and Class C decision. Seven distinct fixture
source hashes and local JUnit/stdout hashes matched their receipts. The f59 tree
matched, and 2394 changed only the audio test. Baseline comparison was independently
recomputed: 6,160 → 6,217 named cases, +58/−1, no common-case status changes and
unchanged local skip IDs. No actionable finding remained in that reviewed packet.

The process evidence proves the seven actual enablement flags with fictional
configuration. Keyword input/priority are synthetic; neutral voice cases cover
handler guards. It does not prove exact effective private configuration, all
commands/publication paths, browser launch, legacy ingress or actual private
recovery. The report and final answers retain those limits.

The same reviewer checked final hosted provenance and wording after the dispatch
blocker was recorded. Source trees and successful JavaScript/Ruff log hashes match;
the cancelled Python jobs and absent retry are correctly marked incomplete.
No open finding remains. This review does not waive the missing hosted gate.

## Audio regression gate repair

The first hosted run on f59 failed one Linux 3.11 audio test: its spy observed two
`close` calls instead of one. Production `get_pcm_from_wav` already uses a context
manager. The test replaced the reader's `close` with a closure retaining the
reader/bound close method, creating a reference cycle. Independent reproduction
observed one call after return, then a second from `Wave_read.__del__` after
`gc.collect()`. Garbage-collector timing made an already-closed handle fail.

Commit `2394bb32` changes only `tests/test_audio_convert.py`. A retained proxy
tracks context closure without replacing the underlying finalizer method. Both
normal and error tests assert one context close and the actual reader's `_file`
is `None` before releasing it. The focused file passes all six tests. The reviewer
confirmed the correction is sound; no production audio change was made.

## Gate evidence

| Gate | Receipt and scope |
| --- | --- |
| Full local regression | [local-regression.json](local-regression.json): f59, 6,181 passed / 36 skipped / 93 passing subtests, zero failures/errors, 234.90 seconds. |
| Focused integrated selection | 133 passed before the last extra publication test; final control file 36 passed, plugin selection 24 passed, native recovery six passed. Full local includes their final forms. |
| Process transition / supported CLI | [integration.json](integration.json): actual held plugin callback, closed HTTP 503, health 200, positive settled drain, unknown handler denial, four-DB continuity, graceful candidate/fallback exit. |
| Seven actual callbacks | [plugin-callbacks-integration.json](plugin-callbacks-integration.json): seven neutral handlers under lease, seven rejections before entry after closure. |
| Legacy exclusion | [ingress.json](ingress.json): gateway test passes, direct bypass remains; OS-boundary acceptance fails. |
| Recovery | [recovery.json](recovery.json): six native-schema tests; isolated restore, migration/idempotence, corruption rejection, unknown files and explicit later-data reconciliation. |
| Initial hosted run | [hosted-initial.json](hosted-initial.json): f59 run 42725122390; one Linux 3.11 test-spy failure, other four jobs pass; preserved as failed evidence. |
| Corrected hosted run | [hosted.json](hosted.json): exact 2394 source. JavaScript/strict TypeScript/build/Ruff pass. Three Python jobs cancelled with cause unknown and no retrievable JUnit. The targeted retry stayed queued with no second attempt. Manual dispatch returned HTTP 422 claiming Actions disabled; read-only APIs say enabled/workflow active. Gate **INCOMPLETE**; no settings changed. |

The full local suite was not needlessly rerun after a test-only spy change. The
focused test repair passes; corrected-source hosted qualification is blocked by
the unresolved Actions dispatch state. Runtime
source/371-file manifest, dependencies and CI workflow are unchanged from f59;
old 005c receipts are retained only as the comparison baseline, not substituted
for new executable validation.

Supporting JSON/AST/F-class lint, relative document links, intended diff and
runtime equality are checked at publication. Private logs, JUnit reports and
fictional fixture directories remain outside Git; only sanitized receipts and
self-contained fixture source are published. Hosted cancellation alone is not
test success, nor is a positive fixture drain proof of legacy quiescence.
