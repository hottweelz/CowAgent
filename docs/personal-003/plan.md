# PERSONAL-003 implementation and acceptance plan

Baseline: PR #9 remains draft/unmerged at adbe2105; PR #10 remains draft/unmerged
at 6aa1b07d49a7ffa2ad69a7f60ec73d5ad669160d. Branch codex/bullgod-personal-003
starts exactly there and will target codex/bullgod-personal-002. All 29 final
regression and 18 native source hashes matched before edits. PRs #4–7 remain
outside the development dependency chain. Live 127.0.0.1:9899 is unchanged.

## Design

Use the existing owner commitment, native scheduler and ConversationStore.
Scheduled responsibility is the trigger; a new/material result can create an
attention finding and an evidence-bound proposal. Pending decisions remain
visible without repeated generation or an unrestricted model-thinking loop.

Observe current identity, revision, active status and explicit read grant;
interpret deterministic qualified news with one bounded tool-free native model
call when semantic judgment is useful; decide within a typed action vocabulary;
act within the existing read/own-state scope or save a proposal; atomically
record the run, verified result and attention; report only meaningful findings.
A quiet scheduled check records completion without another owner notification.

Read grants add an owner-editable expiry and minimum interval to the existing
read_authorized field. Stable grant identity binds agent, commitment and exact
endpoint. Owner revocation, changed revision and expiry are rechecked before
retrieval and final delivery. Legacy approved reads retain their prior scope;
new proactive behavior requires an explicit owner opt-in. State/history writes
are bounded internal bookkeeping; these grants never permit external posting.

The native model adapter selects profile/session routing and receives qualified
source data with no tools and no transcript mutation. Its output can narrow
selected IDs or suggest typed decisions. It cannot introduce a URL, authority,
new goal or executable instruction. A failed/invalid/timed-out model evaluation
stays failed, preserves owner intent and does not mark news delivered. A
transport timeout is not a universal hard cancellation guarantee; late output
cannot bypass durable revision/claim checks.

Attention items have stable event/commitment identity, source references, reason,
reviewable scope, status and expiry. Dismissal preserves history. Approval,
denial and dismissal require authenticated owner intent. Publication proposals
bind exact saved draft text and sources; even approval cannot execute without a
supported separately authorized connector. No publisher is added in this task.
Existing PERSONAL-001 approved file actions remain supported and visible.

## Ownership and sequence

- Luna: read-only PR/source baseline and native model-route mapping (complete).
- Terra 6.1: commitment-store grant/attention/decision transactions and tests.
  Atomic authority, delivery and recovery integration justify this assignment.
- Terra 6.1: native tool-free semantic adapter and request timeout plumbing/tests.
  Native profile/session/provider integration justifies this assignment.
- Luna: existing conversation attention UI, grant controls, decisions and focused
  UI checks. Preserve source selection and stale-response fences; support zoom.
- Lead: CommitmentService/API/scheduler/context integration, integration tests,
  isolated real-model journey, docs, final gate and publication.
- One independent engineering review after integration; targeted follow-up only
  for concrete findings. Luna evidence reconciliation verifies the final journey.

## Required evidence

1. Focused guarded tests for triggers, claims, standing grants/revocation,
   decisions, quiet checks, deduplication, failures/timeouts, concurrent callbacks,
   restart/model changes, owner/agent/guest boundaries and source preservation.
2. Actual browser controls and 200% zoom; verify focus, keyboard operation,
   wrapping, state labels and notification dismissal without history deletion.
3. All 28 numbered acceptance steps from the user specification in one retained
   isolated owner journey. GPT-6 Luna through the existing Pooler; GPT-5.6 Luna
   for continuity. End the owner interaction before the native scheduler runs.
   Prove at least one unattended real HTTPS fetch under the saved grant. Label
   overlapping/update/error/timing fixtures separately; no production action.
4. Pause/revoke owned activity; stop owned app, relay and browser; preserve data,
   failures and source bindings. Keep existing private runtime data untouched.
5. Complete guarded local regression on final executable source, final Node
   checks and independent source/evidence review. Preserve prior valid evidence.
6. Inspect candidate hosted checks once available. The existing control-plane
   failure is documented; no repeated dispatch, settings change or runner audit.
7. Publish docs/personal-003/README.md and receipts, commit/push the named branch,
   open/attach a draft PR against the verified baseline, verify upstream 0/0
   with fetch --no-prune. Do not merge or close earlier PRs.

The completion audit must map exact acceptance steps 1–28 and all phase invariants
without substituting fixture behavior for unattended live retrieval. Source,
local tests, native integration, hosted availability and deployment are separate
claims. Original untracked AGENTS.md and historical evidence remain preserved.
