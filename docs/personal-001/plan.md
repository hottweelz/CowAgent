# PERSONAL-001 implementation plan

Base: PR #8 merged as `1cc6ef1ee65cf8691b12a93b47ce5a02f3d5c348`.
Its tree matches reviewed head `a2994b1a` exactly. Retained regression and runtime
evidence hashes match; GitHub has no head checks or review threads. Local evidence
qualifies this merge under BULLGOD-RESET-001's separate evidence layers. No hosted
result is inferred. Branch: `codex/bullgod-personal-001`.

## Product slice

Deliver the twelve-step owner goal/restart/remember/approve/action/result scenario
in `docs/bullgod-reset-001/README.md`. Keep native CowAgent conversation, identity,
storage, tools, skills and permissions. Add an owner-visible continuity card in
the existing chat. No automatic action resume, worker requirement or new scheduler.

- A thin helper uses the existing ConversationStore database and agent binding
  for explicit goal/progress/pending decision/next step, owner memory with source
  turn/time, and one-action approval/result records.
- Memory can be corrected or forgotten. Only current accepted facts enter personal
  retrieval. Explain that original transcripts are separate retained history.
- Prompt context reloads the current accepted records each turn. Agent/session IDs,
  not model names, own all state. Restricted delegated workers never inherit it.
- Authenticated owner routes require an exact enabled profile and existing owned
  session. Model output may suggest but cannot approve or silently save memory.
- A proposed workspace write binds immutable path/content/source to one action ID.
  Owner approval is explicit and expiring. Atomically claim once before effects;
  execute native write/read through the existing permission gateway and broker.
  Preserve uncertain outcomes across restart and never replay them automatically.
- Show actual runtime tools/skills and their limits. The first supported action is
  a bounded text-file write with readback; no broad mode escalation is persisted.

## Ownership and interfaces

Storage worker owns `agent/memory/personal.py` and storage tests. It provides
`PersonalStore(conversation_store)`: `snapshot(session_id)`,
`save_goal(session_id, fields, source_seq, revision)`,
`remember(session_id, text, source_seq)`,
`correct_memory(session_id, memory_id, text, source_seq, revision)`,
`forget_memory(session_id, memory_id, revision)`,
`propose_action(session_id, path, content, source_seq, expires_at, workspace_root)`,
`decide_action(session_id, action_id, decision)`,
`claim_action(session_id, action_id)`,
`finish_action(session_id, action_id, status, result)`, and `context(session_id)`.
All methods scope to the supplied native store's agent ID. Mutations validate a
real visible owner source turn and revision where applicable. Action bindings
are immutable; approved → executing is an atomic one-way transition.

API/action worker owns `agent/personal/service.py`, `channel/web/api/personal.py`,
route registration and API/action tests. GET/POST `/api/personal/<session_id>`
returns `{status: "success", identity, continuity, memories, recent_goals,
actions, capabilities, memory_retention_note}`. POST `operation` is `save_goal`,
`remember`, `correct_memory`, `forget_memory`, `propose_write`, `decide_action`
or `execute_action`, with corresponding storage fields. `decide_action` only
records approve/deny; `execute_action` requires a current approved action and
executes once. UI can call both after an explicit Approve and execute click.

UI worker owns a new chat continuity module, its styles/template/script wiring,
session/history refresh hooks and focused UI checks. Render escaped text, clear
errors, source references, current memory and exact proposed action. Guard stale
responses when the active agent/session changes. Do not present model text as an
owner decision or hide nonterminal/failed execution.

Lead owns prompt integration, isolated model connection, final integration,
acceptance, docs, review, handoff and Git. Workers must coordinate interface
changes before use; no concurrent edits to shared files.

## Verification

1. Focused storage/API/tool tests: agent/session isolation, additive persistence,
   correction/forget retrieval, source validation, stale revisions, denied/expired
   approval, exact binding, concurrent double execution, restricted file boundaries,
   readback, failure/uncertainty and no restart replay.
2. Native UI/API exercise on independent port/data/workspace/profile, including
   restart and model change. Real conversation uses GPT-6 Luna through the existing
   Pooler with fictional data. No OAuth-token handling or credential changes.
3. One independent engineering review and full guarded local regression after
   integration; preserve source-bound receipts. Hosted state remains separate.
4. Publish implementation as a new draft PR; PR #8 is already merged. Do not merge
   PERSONAL-001 or change PRs #4–7. Live CowAgent at 9899 remains unchanged.
