# PERSONAL-004 independent engineering review

- Reviewer: delegated Codex reviewer; requested GPT Sol 6.1/high for the
  registered identity, private context, approval and durable execution boundaries.
- Date: 2026-11-10 18:32 UTC.
- Base: `ab13b789`; branch: `codex/bullgod-personal-004`.
- Result: PASS for the reviewed source scope. All five concrete findings below
  are closed. This is one review with targeted fix checks, not repeated reviews.
- Scope: collaboration ledger/executor/tests, native prompt tool override,
  owner service/context composition, model defaults/launcher and research UI,
  CSS and Node checks. The parent owns integration, native acceptance, final
  regression, handoff and Git sync.

## Findings and closure

| Finding | Evidence and correction | Closure |
| --- | --- | --- |
| P2: research history disappeared in a new owner conversation | A synthetic completed request remained attached to an agent-scoped commitment but was absent from the next conversation. History is now agent scoped and returns `source_session_id` and `can_mutate`. Approval/execution still require the original owned conversation. | Source checked; synthetic history/origin/read-only checks passed. Focused tests cover completed history and another agent's exclusion. |
| P2: default-agent model binding differed from native routing | A synthetic default profile pin advertised GPT-5.6 while the native default followed the global GPT-6 setting. `_target()` now uses the initializer's default-aware precedence. | Source checked; synthetic default-route check passed; explicit non-default pins remain distinct. |
| P2: target transcript and cached model messages diverged | Direct streaming saved two target messages without updating the cached Agent. The executor now calls `sync_session_messages_from_store()` for that target-owned session and requires both messages. | Source checked against the existing bridge method; focused fixture checks cached roles/content and visible uncertainty if synchronization fails. |
| P1: private path aliases were opened before validation | Synthetic target DB/context symlinks could open owner data while the old resolved-path equality checks passed. `_check_private_context()` now runs before Bridge or target-store initialization. It rejects registered root overlap, including disabled profiles; escaped native index/context paths; and hard-linked private files. | Source ordering checked. Four focused fixtures cover DB symlink, MEMORY.md symlink, MEMORY.md hardlink and nested disabled profile, with zero Bridge calls and no replay. The intended shared ConversationStore namespace remains unchanged. |
| P2: UI confirmations ignored returned research state | Synthetic Node VM responses reproduced an uncertain execution reported as finished and expired approval reported as approved. UI messages now use `research_operation.status`; failure/uncertainty set the error state. | Source checked; the Node checker has exact assertions for both reproduced cases and their error flags. |

## Verification and limits

The reviewer used repository source, isolated temporary SQLite/path fixtures and
a synthetic Node VM. No production/private state, running application, network
or model was accessed. The implementation worker reported 24 focused checks
passing after the boundary fix; the UI worker reported the updated Node checks
passing. Those valid checks were reused, not rerun solely for bookkeeping.

Review also covered immutable proposal binding, one-shot claims, abandoned-claim
uncertainty, changed-binding fences, source ID/exact excerpt validation, empty
tool schemas, escaped UI fields/HTTPS links, separate approval/execution controls,
cross-conversation read-only history and delayed-response fencing.

Source provenance checks do not independently establish publisher truth or model
judgment. The executor retains its documented single-process contract and does
not automatically replay uncertain work. Metadata checks assume the same local
user does not replace files concurrently during initialization; this is not a
hostile same-user filesystem isolation claim. Real registered-specialist
execution, restart acceptance, full final-source regression and actual 200%
layout checks remain parent-owned gates, not results of this source review.
