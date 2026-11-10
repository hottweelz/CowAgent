# FIRST-BOOTSTRAP-002

**CLASS C — NO-GO.** The future candidate now supports private operator drain and
qualified execution of the seven known plugins. A live transition remains blocked
by unproven external admission exclusion, unbounded legacy background effects and
unqualified restoration of the actual private state.

Published as [draft PR #7](https://github.com/hottweelz/CowAgent/pull/7), based on
the actual PR #6 head `fcbc0d25`. PRs #4–7 remain dependent and unmerged. Live PID
28093 continues at `127.0.0.1:9899`; its loaded modules are not inferred from Git.
The [concrete transition policy](maintenance.md) states the technical prerequisites,
private recovery scope, startup effects, abort conditions and remaining decisions.

## Delivered controls and evidence

- [Plugin lifecycle matrix](plugins.md): seven reviewed classes, their actual
  configured flags, startup effects, local callbacks, known child work and explicit
  unsupported paths. Source/class/handler checks retain fail-closed behavior for
  imports, replacements, failures and unknown activity. Remote image jobs,
  extensible CLI commands and plugin management remain blockers when used.
- [Private operator control](operator-control.md): launch-only private directory,
  genuine owner/PID/epoch binding, explicit one-shot close-and-observe grant,
  durable sanitized claims/receipts and deterministic bounded observation. The
  existing trusted OS-account boundary is not human-presence authentication.
- [Real service integration](integration.json): modeled legacy → candidate with
  all seven enabled → unsupported variant → restored master on disposable 19890.
  A held real Keyword callback blocks drain; fresh submission returns 503 and
  health stays 200. Actual completion produces a positive receipt with all nine
  components. Replaced handler correctly blocks drain. Every owned process exits 0.
- [Seven callback cases](plugin-callbacks-integration.json): a separate candidate
  enters each real registered handler under a lease on neutral voice input; all
  seven reject before handler entry after close. These are neutral guard paths,
  not every plugin command or remote effect. Original accepted process evidence
  is retained without replay.
- [Recovery design](recovery.md) and [native four-database fixture](recovery.json):
  SQLite online backup, isolated restore, real merge migration/idempotence,
  identity/history continuity, unknown-file/mode/symlink preservation, corrupt or
  missing-entry rejection and explicit later-user-data reconciliation. The
  [current interrupted-startup check](interrupted-startup.json) stops f59 after
  private control publication but before observation/listener, then verifies a
  fresh replacement, stale-control rejection and four-database continuity. It
  does not claim a crash inside a transaction. The normal process receipt also
  proves candidate/restored fallback startup.
- [Legacy ingress](ingress.md): disposable gateway closure works but direct
  listener access bypasses it. PF inspection was denied; no OS rule was applied.
  A concrete private-anchor proposal includes loopback, keep-alive, forwarding,
  observation, reversal and unrelated-application checks. It remains unqualified.

## Source, preservation and validation

Executable commit `f59a6e91152900d709cad1775b2756cf25b316c0`, tree
`988926c42ab9638f129b6b0ea1970c99db0d447a`, has 371 startup-manifest Python files:
`11e67da08cc9b5efa7b1f8220dbbe4ba26fe208c3b992a6bcae64f17e47a1279`.
Later commit `2394bb3201b26b49ccd30131fd46d902bf0f837c` changes only an audio test
spy to remove garbage-collector timing dependence; production source is identical.

The [full local gate](local-regression.json) passed once on f59: **6,181 passed,
36 skipped, 93 passing subtests**, zero failures/errors. Six focused audio tests
pass after the test-only correction. The first hosted run's single Linux 3.11
close-count failure is retained in [initial evidence](hosted-initial.json), with
its deterministic finalizer-cycle diagnosis; it is not a passing gate.

**The corrected-source hosted gate is incomplete.** JavaScript (39 web + five
desktop), strict TypeScript/build and Ruff passed. The three Python jobs were
cancelled, with no retrievable JUnit or established cause. One targeted retry
stayed queued without an actual second attempt. A supported manual dispatch was
then rejected HTTP 422: **Actions has been disabled for this repository.**
Read-only APIs contradict that response: Actions is enabled, the workflow active,
and the repository neither disabled nor archived. The cause is unresolved and
settings were not changed. The [hosted receipt](hosted.json) preserves both
observations; no passing Python matrix is claimed for 2394. The prior f59 matrix
had matching 6,217 named IDs and unchanged platform skip sets, with its audio-test
failure retained. [Review and validation](review.md) records the review and limits.

[Baseline preservation](baseline.json) confirms master `f6593497`, PR #4
`a507a400`, PR #5 `8d182026`, PR #6 `fcbc0d25`, primary HEAD `a507a400`, the two
recovery refs, all five retained recovery artifacts and all seven original
untracked files. `git fsck --full` passed with 44 dangling/unreachable lines and
no corruption; no pruning or GC was performed. [pCloud settings](pcloud.json)
show six Backup roots without overlap and zero Sync pairs; settings were unchanged.
The [PR chain](pr-chain.json) remains draft/unmerged. Final process and artifact
preservation are in [postflight.json](postflight.json); Git publication is recorded
in the handoff.

The actual [live-state manifest](live-state-manifest.json) inventories membership
and metadata for the selected data root, runtime workspace and source-mode plugin
tree: 64, 78 and 100 entries. Four SQLite databases use WAL; global memory and
conversation storage share one DB, two secondary memory DBs are distinct, and
recovery has its own DB. Aggregate terminal history does not prove runtime idle.
Unknown/unselected files are explicitly retained for reconciliation. No private
live backup, restore, checkpoint, vacuum, journal change or migration was performed.

## Required final answers

| Question | Answer |
| --- | --- |
| 1. Can new external work be reliably excluded from PID 28093? | Not demonstrated. It still exposes direct loopback admission. The tested gateway has a bypass; a scoped OS fence has not been qualified or authorized. |
| 2. Which background producers remain able to create work? | Already accepted chat/native/parallel work, scheduler callbacks, recovery dispatch, memory sync, evolution if runtime-enabled, and plugin children/remote effects. No saved scheduler tasks and an off evolution flag do not prove legacy in-memory inactivity. |
| 3. What does each enabled plugin do? | CowCli dispatches administrative/skill/memory commands and children; Godcmd administers configuration/session/plugins; Keyword returns matched content or downloads files; Banwords filters input/replies; LinkAI performs API/summary/image work and polling; Role changes session roles; Finish handles unknown command replies. See the complete effects/completion matrix. |
| 4. Which plugin lifetimes can the new coordinator certify? | Exact known constructors and local callbacks, plus instrumented CowCli future/thread and LinkAI polling/publication lifetimes through actual completion. It cannot certify arbitrary delegated commands, surviving remote image jobs, changed/unknown code or the old PID. Those paths retain sticky blockers. |
| 5. Does the candidate produce a valid receipt with the real enabled-plugin configuration? | Yes for the same seven enablement flags with fictional safe configuration: actual service + supported CLI, held callback then complete drain, and seven neutral callback cases. No claim that private effective configuration or every plugin command was executed. |
| 6. Is a safe private invocation implemented and validated? | Yes within the existing same-UID/root trust boundary. Private provenance, genuine initialized owner, PID/epochs, explicit grant, one-use IDs, replay/concurrency/timeout/durability and coverage refusal are tested. It sends no signal and cannot reopen or cancel work. It is unavailable in PID 28093. |
| 7. Is the actual durable-state manifest complete? | Membership/metadata enumeration is complete for the three selected filesystem roots at capture, with active/unselected state and unknown files identified. It is a scoped inventory, not a verified private backup; injected environment, external account/service state and runtime memory are outside it. |
| 8. Is four-database recovery consistent and reproducible? | Yes on native-schema fictional state using SQLite online backup and a closed file-set interval, with isolated candidate/fallback and migration/restore checks. Independent DB snapshots alone do not make a multi-DB/file atomic snapshot. |
| 9. What remains unverified about actual private recovery? | Authorized copy destination/retention/access, the real closed-write interval, complete content continuity, actual private migrations/restoration, and reconciliation of later local or remote effects. No private live backup was created. |
| 10. Can one-time legacy uncertainty be bounded without falsifying quiescence? | A concrete policy is documented, but not yet qualified. Enforceable ingress, producer/effect limits and actual recovery must succeed first. Silence, elapsed time or operator acceptance alone cannot replace these controls. |
| 11. What decisions are needed before transition? | A scoped disposable OS-fence experiment then separate live-rule approval; actual private backup/restore scope; specifically bounded interruption/reconciliation risk; enumerated startup/shutdown and environment handling; exact candidate/fallback and one live stop/start window. APFS, approvals, production activation and merges remain separate. |
| 12. Is Class B supportable? | No. Class C remains justified by the demonstrated direct ingress bypass and unresolved legacy producer/private-recovery limits. Candidate plugin coverage and operator invocation are now concrete tested controls. |

The hosted gate first needs the contradictory Actions dispatch state resolved,
then the exact-source Python matrix. The remaining live-transition work is the
narrowly scoped OS-fence qualification and approved private recovery rehearsal
described in the policy. Do not repeat the broad legacy audit or treat new
candidate instrumentation as evidence about the old process.

The [requirement completion audit](completion-audit.md) maps all nine phases to
current evidence. The hosted Python gate remains incomplete; a valid Class C
decision is not a claim that every requested validation gate passed.
