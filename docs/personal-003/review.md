# PERSONAL-003 independent engineering review

Result: **PASS for the reviewed source and targeted fixes.** No open finding
remains within that scope. This receipt does not certify completion of the
whole milestone.

Branch: `codex/bullgod-personal-003`. Reviewed baseline:
`6aa1b07d49a7ffa2ad69a7f60ec73d5ad669160d` (PERSONAL-002). The reviewer read the
project instructions, README, MEMORY, latest handoff, owner specification and
[implementation plan](plan.md).

The parent assigned a GPT Sol 6.1/high review because standing authority,
revocation, atomic delivery and model advice cross several security and durable
state boundaries. The runtime model identity was not independently attested.
The parent retained lifecycle, acceptance, handoff and Git ownership.

## Reviewed paths

- `agent/memory/commitments.py` and `agent/memory/personal_context.py`:
  grant conditions, claims, quiet completion, attention, decisions and context.
- `agent/personal/commitments.py`, `agent/personal/scheduling.py` and
  `agent/tools/scheduler/integration.py`: scoped execution and native scheduling.
- `agent/personal/interpretation.py`, `agent/protocol/models.py`,
  `bridge/agent_bridge.py` and `models/openai_compatible_bot.py`: native model
  routing, tool-free interpretation, output validation and request timeout.
- `channel/web/static/js/chat/commitments.js` and
  `tools/check-commitments-ui.mjs`: owner controls, actual API fields, attention
  states and source references. The pending zoom/CSS change is excluded.
- Relevant initiative-store, interpretation, service, context and scheduler
  tests were inspected with the implementation. Existing native conversation
  and personal-store methods were traced where they defined the boundary.

## Findings and closure

All six original findings were P2 and are closed:

| Finding | Verified correction |
| --- | --- |
| Real drafts expose `item_id`, so the publication-proposal button was absent. | The UI accepts the actual persisted item ID. The server still binds the immutable draft and sources. |
| Grant limits were confused with the derived grant contract; model scheduling context could overlook expiry. | The UI uses derived `grant` metadata and separate editable limits. Context includes `read_grant`; schedule status also accepts derived expiry. |
| Terminal attention remained active, blocked notices could not be dismissed, and pending publication was described as approved. | Active attention and history are separate; blocked notices can be dismissed; outcome wording follows persisted status. |
| A new material event reused an earlier denied proposal, while briefing text claimed a pending decision. | Proposal keys bind event content and commitment revision. Only a current, pending proposal is reused. Briefing text points to saved review status without claiming approval is pending. |
| Successful recovery left frequency-blocked attention marked blocked. | Atomic completion resolves undismissed unread and blocked failure items. |
| A valid owner in a later conversation could not propose publication of a saved draft. | The proposal accepts an owned source turn from the later session while retaining agent, commitment and draft checks. |

A targeted follow-up caught a remaining proposal-revision case: an owner edit
made the reused pending proposal impossible to approve. Current-revision reuse,
revision-bound publication keys and an explicit stale flag closed it. Earlier
scope remains inspectable, deniable and dismissible; the UI offers no approval
control for it.

## Final pass scope

The reviewed implementation preserves native permission checks and durable run
claims. Current intent, revision and grant expiry are rechecked before final
completion. Quiet scheduled checks record completion without another message.
Delivery and attention changes remain in the existing SQLite transaction.
Approval records a decision; no publisher or external-effect executor is added.

The later streaming compatibility change was reviewed separately within this
same bounded review. It makes one native model request with no tools, caps
collected text at 16,000 characters, requires a valid stop, rejects tool calls,
invalid JSON and late output, and closes the iterators. Selected IDs and typed
proposals remain advisory data. The registered owner ID changes grant metadata;
database lookups retain the existing native storage namespace.

The final context change also passed targeted review. At most five recent
checks retain separate run IDs, status, trigger, briefing excerpts and bounded
source references. Conversation-failure lookup explicitly filters registered
owner, current session, top-level run and conversation task source. It exposes
fixed reason text instead of raw errors and retains the context size cap.

## Evidence and limits

The reviewer used source inspection and guarded disposable-store probes. Those
probes reproduced the denied-proposal reuse, stale proposal revision,
later-session rejection and blocked-after-success cases before correction.
Targeted source checks closed the fixes. No live service, model, credentials or
production state was accessed; accepted interactions were not replayed.

Focused automated results reported during follow-ups belong to the parent and
implementation workers; the reviewer did not independently rerun those suites.
Final full regression, source bindings, all 28 native acceptance steps, hosted
availability and cleanup remain parent-owned completion gates. Transport and
elapsed checks reject late model results but do not prove universal provider
cancellation. The pending 200% zoom fix and its browser validation are **not
reviewed or certified by this receipt**. Hosted CI availability was not reinvestigated.
