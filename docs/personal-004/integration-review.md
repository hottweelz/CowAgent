# PR #12 integration review

**Decision: PASS for integration review. No blocking source or compatibility
finding was identified.** Recommend a normal merge after the maintainer's explicit
integration decision. This review does not merge the PR or authorize deployment.

- Reviewed: 2026-11-10 14:08 EST.
- PR: [PERSONAL-004](https://github.com/hottweelz/CowAgent/pull/12).
- Reviewed source head: `f52e89f19533bbb367711628472ac0efd9ab42cd`.
- Current master/base: `ab13b789e28e3efc8571e6406acda8c88e914b77`.
- Relationship: zero master-only commits, two PR-only commits; master is an
  ancestor. GitHub reports mergeable. No rebase or conflict resolution is needed.
- Team: lead integration/source review; one GPT-6 Luna/high read-only evidence
  qualifier. Applied registry-listed STE code-review and efficient-evidence guidance.
  The prior independent engineering review is retained, not repeated recursively.

## Current GitHub conditions

Read-only queries found no repository rulesets, master protection (HTTP404:
Branch not protected), submitted PR reviews, or unresolved review threads. The
reviewed head has no reported checks/statuses. Those empty lists are **not a
hosted CI pass**. No Actions setting, workflow, branch rule or PR state changed.
The PR remains draft and unmerged. Prior PRs #9–11 are already integrated in the
base; this PR has no dependency on activating the deferred PR #4–7 chain.

## Compatibility and authority assessment

| Surface | Assessment |
| --- | --- |
| Owner API | Uses existing authenticated owner, origin and persisted source-turn checks. Preparation, approval and execution are separate. An existing read grant cannot authorize specialist execution. |
| Registry/runtime | Resolves the registered target through native AgentBridge with a fresh target-owned session. Persona, memory manager and configured model stay native. Existing generic delegation and external fictional-record adapters are unchanged. |
| Persistence | New research table/index and process marker are additive to the existing database. Durable claim precedes effects. Result and owner message commit together; repeats reuse the same state, and abandoned/uncertain work cannot replay automatically. Existing records are not rewritten. |
| Context/export | Guest/restricted-runtime exclusions remain. Target path metadata checks precede initialization. The source-only native call has no tool-dispatch loop. Output must match frozen source IDs/excerpts and typed classifications; arbitrary private prose is rejected. |
| Conversation/UI | Research history is agent-scoped; controls remain tied to its original owner conversation. Final-state text, stale-response fencing, unavailable-target continuation, keyboard navigation and status contrast are covered. BullGod retains the personal goal. |
| Models | New unpinned developer instances select the newest supported numeric catalog version within the chosen family. Existing explicit pins remain. GPT-6 Luna is accepted; GPT-5.6 requires explicit last-resort selection and automatic developer fallback is off. |
| Existing callers | Optional prompt tool override preserves the old default when omitted. The launcher signature retains existing positional arguments and adds the family argument last. There is no workflow, startup-service or deployment change in this PR. |

## Retained verification qualified to this head

The independent evidence qualifier compared all **13 final application/test
hashes** and all **seven native runtime hashes** with current source. They match.
The retained regression log confirms **6,210 passed, 36 skipped, 93 subtests
passed**. This is reused valid evidence, not a new run in this review.

The full run overlapped a seven-line capability-guidance correction; the final
context test log then passed **5/5**, and subsequent real same/new-chat responses
were accurate about the supported workflow. A later CSS foreground correction
has final-screen 200% keyboard/layout evidence and **11.87** measured contrast.
One trailing test-file space was removed with identical Python AST. These are
explicitly qualified changes; the whole final tree is not described as a new
full-suite run. Syntax, Ruff, Node UI and whitespace results remain documented.

Actual GPT-6 Luna Pooler acceptance shows an approved HTTPS news read and one
registered NewsAnalyst execution with its own synthetic native context, no owner
memory marker and zero tools. Unapproved/denied requests made zero specialist
calls. Exact source provenance, repeat/restart continuity, later-chat read-only
history and BullGod continuation when the specialist is unavailable are supported
by consistent receipts. No model call or accepted native interaction was rerun.

Evidence: [local regression](local-regression.json),
[engineering review](review.md), [native receipts](native-validation.json),
[independent native audit](acceptance-audit.json), [runtime binding](runtime-source.json),
[UI checks](ui-validation.json) and [preservation](preservation.json).

## Remaining limits and integration boundary

- Hosted CI remains unavailable/unverified. No configured required check was
  bypassed or weakened. If repository rules or the source/base change before
  merge, recheck the changed condition; do not infer a hosted pass.
- Native acceptance used a real **headline-only** source. Verification establishes
  the excerpt's provenance, not publisher truth or relevance/priority accuracy.
  Full-article fetching/import and external publishing are outside this action.
- Restart evidence covers the recorded single-process sequence, not power-loss,
  multi-host execution, or universal hard cancellation. Filesystem metadata checks
  do not defend against concurrent same-user path replacement.
- Production deployment is a separate decision. This review made no live service,
  private-data, credential, approval or APFS change and does not reactivate legacy
  maintenance. The prior owned acceptance process is recorded as stopped.

This review adds only documentation and the required handoff. Application and test
bytes remain those of the reviewed head. The final publication step verifies
upstream synchronization; PR state remains unchanged.
