# PERSONAL-003: initiative and permission-aware follow-through

Published for review as draft [PR #11](https://github.com/hottweelz/CowAgent/pull/11)
against PERSONAL-002. Local and native acceptance are complete with the limits
below. Hosted CI remains unavailable; no merge or deployment was performed.

BullGod can check an owner-approved responsibility through the native scheduler,
judge sourced developments with its selected model, retain a quiet check without
another notification, and bring a persistent decision back to the owner. It uses
the existing conversation database, registry, model route, tools and permission
gateway. There is no new scheduler, unrestricted thinking loop or publisher.

## Baseline and scope

Branch `codex/bullgod-personal-003` starts at validated PERSONAL-002 commit
`6aa1b07d49a7ffa2ad69a7f60ec73d5ad669160d`. PR #10 remains draft against PR #9's
`codex/bullgod-personal-001`; PR #9 remains draft against master. The dependency
chain is preserved; no PR is merged by this task. PRs #4–7 stay deferred.

| Implementation | Responsibility and compatibility |
| --- | --- |
| `agent/memory/commitments.py` | Additive run evaluation and attention records in ConversationStore; standing-grant limits, stable decisions, atomic quiet/delivered completion, bounded context. Existing commitments default to semantic initiative disabled. |
| `agent/personal/commitments.py` | Observe current intent/grant, call the existing approved reader, qualify/deduplicate articles, optionally interpret, then record or request review. Existing owner API authentication and source checks remain. |
| `agent/personal/interpretation.py` | One native tool-free streaming model request. Profile/session model selection is retained. Output can select supplied article IDs and propose typed decisions, not supply authority or arbitrary tool arguments. |
| `agent/protocol/models.py`, `bridge/agent_bridge.py`, `models/openai_compatible_bot.py` | Optional positive finite request timeout, forwarded to provider transport; stream cleanup. Existing calls without the option retain their defaults. |
| `agent/personal/scheduling.py`, `agent/tools/scheduler/integration.py` | Existing typed scheduler pointers and durable occurrence claims. Quiet completion is a completed native run. Revoked/expired grants cannot execute. |
| `agent/memory/personal_context.py` | Current owner context includes separate recent checks, scoped conversation failures, attention and current permission/schedule state. Guest and restricted-worker exclusions remain. |
| `channel/web/static/js/chat/commitments.js`, `channel/web/static/css/commitments.css` | Attention, proposal review, grant controls, execution history and approved actions in the existing conversation. |

## Initiative and standing authority

The sequence is **observe → interpret → decide → act or request → record →
report**. Due responsibility triggers a bounded check. A meaningful new or
materially updated story creates a finding and may create a decision. A pending
decision stays visible until reviewed; it does not cause repeated execution.

Owner controls explicitly save the commitment, preferences, schedule, read grant
and semantic-initiative opt-in. A derived grant identifies the registered agent,
commitment, exact endpoint, operation, revision, active conditions, expiry or
revocation, minimum interval, read scope and bounded internal bookkeeping.
An omitted expiry means valid until revoked, not missing authority. Individual
approval is not required for each read within that explicit standing grant.

The accepted workflow reads only `https://tyl.ee/api/news` through the existing
approved JSON tool and native permission gateway. Its own commitment/cache/history
writes are internal bookkeeping. A read grant cannot publish a social post or
authorize another external effect. Models cannot create commitments, renew
grants, change owner intent or choose a new endpoint.

Run evaluations distinguish authorized reads, bounded internal writes, new
approval required, no action necessary, and blocked/uncertain work. Identity,
revision, due time, active status, frequency, expiry and coverage checks are
deterministic. The model only evaluates already-qualified, bounded source data.
At most five selected stories enter this interpretation; fewer or none is valid.
Publisher assertions and ranking/sentiment remain attributed data.

## Attention, decisions and recovery

The conversation card shows active commitments, last checks, meaningful findings,
pending decisions, approved PERSONAL-001 actions, failures and next activities.
Completed, waiting, scheduled, paused, failed and uncertain states stay distinct.
Terminal/stale/dismissed items remain in history. Dismissal hides attention and
preserves the underlying run and decision outcome.

Proposals bind their action, reason, evidence, sources, scope, revision, status
and optional expiry. Current pending proposals are reused, not copied on every
evaluation. An earlier denial is not revived for the same event. A materially
different event can warrant another proposal. Owner edits make old scope stale;
it remains deniable/dismissible and cannot be approved under the new revision.

Publication review binds an immutable saved draft and its delivered sources.
Approval records a decision only. This milestone has no supported publication
connector or execution path; even an approved publication remains blocked. The
native acceptance denied the proposal and did not publish anything.

Durable SQLite claims and occurrence uniqueness prevent concurrent duplicate
execution. Successful delivery, coverage, the assistant message and attention
commit together. A quiet scheduled check updates its ledger/cache without a new
conversation message. Failed/uncertain runs are not successful deliveries.
Existing uncertain-claim acknowledgment rules remain; no external effect replays.
Model changes preserve identity, grant scope, proposals and execution history.

## Native acceptance

The isolated instance used port **19893**, its own workspace/database/profiles,
disposable console authentication and the existing local Pooler. GPT-6 Luna ran
the initial conversation and semantic check; GPT-5.6 Luna ran after restart.
No local inference model was installed. The owner browser was closed before the
controlled native due window, with no fresh owner prompt before retrieval.

| Observation | Evidence and limit |
| --- | --- |
| Unattended actual retrieval | The approved native reader returned 100 current feed records. Run `e1f413c5b4aa4bf8b5f73051a536cf72` delivered one attributed Bitcoin/CPI report, selected with real GPT-6 Luna interpretation, and persisted a tracking proposal. This establishes a bounded live retrieval, not continuous production reliability. |
| Restart and model switch | Commitment, sources, grant and publication decision survived. Native GPT-5.6 Luna conversation recalled them. |
| Repeated source | A labeled response fixture reused the previously reported article. The scheduled run completed quietly with no new message or duplicate proposal. |
| Material update | A clearly labeled fictional institutional-settlement addition to that article produced a new relevant notification through real GPT-5.6 Luna interpretation. It is not real-world news evidence. |
| Revocation | Owner UI revoked the grant. A controlled due-pointer negative case advanced without another fetch or commitment run. The pointer was restored disabled. |
| Timeout | A controlled native conversation timeout remained failed. Goals, memory, commitment, decisions and delivered-message count remained intact. Unit tests also cover semantic model timeout and transport/output handling. |
| Resumed explanation | The final native answer reports all four check outcomes chronologically, attributes the retrieved report, separates the later fixture, and correctly states publication denial, revoked permission and conversation timeout. |

The initial unattended attempt fetched successfully but failed on the semantic
adapter's non-streaming route. It remains a failed run. The adapter now uses the
existing native streaming route; acceptance used a fresh occurrence, not replay.
Two later status answers confused the latest fixture with earlier history.
Compact per-run context and separately scoped conversation-failure records were
added. A request-presence probe confirmed all records reached the native model.
The final chronological question produced the correct explanation. Earlier
answers remain preserved; arbitrary conversational summaries are not guaranteed
accurate and never determine authorization or execution state.

The exact numbered journey is reconciled in [acceptance-audit.json](acceptance-audit.json).
See [native-validation.json](native-validation.json), [runtime-source.json](runtime-source.json),
[context-probe.json](context-probe.json), and [manual procedure](acceptance.md).
Source updates are recorded; accepted execution cases were retained. Final
runtime files match the candidate without an asset overlay.

## Validation and preservation

- [Local regression](local-validation.json): **6,192 passed, 36 skipped,
  93 subtests passed**, zero failures/errors, 209.60 seconds. All 17 changed
  executable/test hashes matched before/after; both Node UI checks passed.
  The receipt retains commands, exact skips and 36 warnings. A baseline
  unused `typing.Any` import produces Ruff F401 in `agent/protocol/models.py`;
  the same result was reproduced from the base commit. No lint suppression or
  CI protection change was made.
- [Independent engineering review](review.md) closed six original findings and
  targeted follow-ups. The small final zoom CSS correction received parent
  source/DOM review and actual browser validation; it is outside that reviewer's
  earlier source scope.
- [200% UI evidence](ui-validation.json) uses a 720×550 CSS viewport at 2× scale
  for 1440×1100 physical pixels. Both panels scroll, labels and keyboard access
  work, chat remains visible, and the input/send controls remain onscreen without
  horizontal overflow. This is effective zoom/reflow, not a claim about a browser
  menu setting. The failed initial layout receipt is preserved separately.
- [Hosted status](hosted-validation.json) reports candidate checks separately.
  Earlier dispatch was rejected as Actions disabled despite enabled metadata.
  No repeat control-plane investigation, enablement or dispatch is part of this
  milestone. No absent hosted check is reported as passing.
- [Cleanup](cleanup.json) confirms the owned service/relay stopped, original
  bootstrap restored, fixture artifacts retained and original PID 28093 still
  listening on `127.0.0.1:9899`. Live service/data, APFS ownership, production
  credentials and approvals were not changed.

Known limits: the inherited scheduler has single-process coordination and a
ten-minute catch-up window; this is not multi-host or power-cut qualification.
Lexical qualification can miss synonyms and ambiguous event relationships.
Semantic evaluation uses bounded input and rejects malformed/late results; an
idle provider must honor its transport timeout, so universal hard cancellation
is not proved. Temporary acceptance roots are not production persistence.
Hosted/platform skips and model-summary uncertainty remain explicit limits.

## Next personal-agent milestone

**PERSONAL-004: optional specialist collaboration.** From one saved sourced
decision, let the owner request a bounded research task from a registered
specialist through the already validated authenticated adapter. Retain the
BullGod commitment and source links, report verified worker results, and explain
unavailability without losing the goal. BullGod must still answer and continue
ordinary responsibilities when no specialist is available. Do not add another
orchestrator or make legacy service migration a prerequisite.
