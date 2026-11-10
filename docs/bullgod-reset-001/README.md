# BULLGOD-RESET-001

BullGod is a persistent personal agent for its owner. Its identity, memory and
commitments should remain useful across sessions and model changes. Delegation
is an optional skill, not its purpose.

**Development now starts from stable master, independently of legacy maintenance.**
FIRST-BOOTSTRAP-001 and 002 are completed investigations. Their Class C findings
remain deployment concerns; resolving them is not a prerequisite for PERSONAL-001.
The running CowAgent at `127.0.0.1:9899` is outside this development baseline.

Published for review in [draft PR #8](https://github.com/hottweelz/CowAgent/pull/8).
Implementation commit: `4595d81a9efac649034f1d7f4b35d92376442e83`.

## Clean integration

Branch `codex/bullgod-reset-001` starts directly at verified master
`f659349785acf98905901a5cc53921436a109dbc`. It does not inherit PRs #4–7.
The [component inventory](inventory.md) maps actual files, dependencies, tests and
KEEP/SIMPLIFY/DEFER/REMOVE FROM ACTIVE DEVELOPMENT decisions.

The small extracted subset is:

- PR #4's filesystem ownership guard and read-only view of an existing approval
  journal. No schema creation, mutation or execution-lock acquisition is allowed
  through the read-only view. Existing owner/mode/authority checks remain.
- PR #4's discovery routing fix: use supplied settings rather than another
  instance's process-global model settings, including existing custom providers.
  Deterministic discovery still does not authorize or perform execution.
- PR #7's independent audio test-spy correction. Production audio is unchanged.
- A small developer launcher and focused tests. It runs ordinary CowAgent from
  a private source/data/workspace copy with a synthetic BullGod profile and
  disposable console authentication, without the maintenance startup machinery.

The larger trusted-runtime reader integration remains on PR #4 because it depends
on inspection/proof/owner lifecycle contracts. PR #5's distributed drain hooks
remain together. PR #6's reports and PR #7's private maintenance/plugin certification
remain references or deferred deployment features. None is partially enabled here.

No old branch, commit, report, recovery artifact or protecting test is deleted.
"Remove from active development" means those experiments are excluded from this
master-based branch and roadmap. Existing master functionality remains supported.
PRs #4–7 stay draft/open. After an explicit integration decision, a maintainer may
close superseded PRs with comments linking the replacement and preserved history.
This reset does not merge or close any PR.

## Personal-agent architecture

Use the native agent and web conversation as the product core:

```text
owner conversation
  → stable BullGod profile + workspace persona
  → relevant conversation/memory + owner-visible commitment state
  → existing model interface
  → proposed action → existing permission gateway → tool or optional worker
  → observed result + provenance → owner summary and persistent continuity
```

The [inventory](inventory.md) locates the existing implementation. AgentRegistry,
workspace context files, PromptBuilder, ConversationStore, MemoryManager, tools,
skills, model routing, permissions and worker recovery are already available.
Use them. Do not add a new registry, model router, memory engine or orchestration
framework to make this diagram work.

Three product gaps matter first:

1. **Inspectable personal memory.** Show source interaction/file and time; make
   owner correction and removal visible and ensure retrieval follows the change.
   File/index metadata exists, but a reliable owner-facing workflow is unfinished.
2. **Durable owner commitments.** A conversation transcript and delegated-worker
   recovery row are not a goal list. Store an explicit continuity summary and
   pending decision linked to the owning agent/session and source interaction.
3. **Permission-aware follow-through.** Show the proposed action, needed scope,
   outcome and next step in conversation. A transient confirmation dialog or
   broad session mode must not be presented as durable, one-action approval.

Identity and durable records are keyed by agent/session identity, not model name.
Changing a supported model must not reset persona, goals, memory or pending
decisions. Provider credentials/configuration remain separate from personal data.
The model can suggest memory/goal changes; authenticated owner actions and observed
tool results determine accepted state and provenance.

## Isolated development

Follow [development.md](development.md). The default instance uses port **19892**,
its own source snapshot, data root, home, workspace, profiles and SQLite files.
No production OAuth credentials, approvals or private memory are copied. Reset
creates another fresh root rather than deleting existing state. Start/stop are
limited to the task-owned instance. The live service does not need an upgrade.

[Development evidence](development-validation.json) separates actual service/UI,
authentication and restart/store checks from model conversation quality. Provider
network access is denied by default; this is a safe development baseline, not a
claim that an actual model has already completed the product experience. A later
model acceptance run needs an explicitly selected disposable provider/local model
and scoped network configuration, without borrowing production authority.

## Four product milestones

| Milestone | Bounded product change | Visible acceptance |
| --- | --- | --- |
| **PERSONAL-001: Identity and Persistent Memory** | Stable BullGod profile/persona, explicit memory with source/correction/removal, and a thin owner-visible continuity card using existing session storage. A minimal goal/pending-decision/action thread supports the complete first experience below; no proactive loop or delegation is required. | Owner introduces a project and preference, saves a goal, leaves and restarts the isolated instance. BullGod resumes with the same identity, correct context and pending decision. Owner corrects/forgets a memory; retrieval reflects it. One approved bounded action is completed and explained. |
| **PERSONAL-002: Goals and Commitments** | Expand the thin card into explicit durable goals, progress, priority, completion/cancellation and pending decisions. Separate owner intent from worker execution/recovery. | Owner resumes two goals after restart, sees accurate priorities and last progress, changes one deadline/decision and completes the other without losing its result history or silently replaying work. |
| **PERSONAL-003: Initiative and Tool Use** | Use existing scheduler/tool mechanisms to notice a commitment that needs attention. Propose by default; perform only pre-authorized bounded actions, with durable result/denial state. | A due commitment surfaces one useful suggestion. A read-only action can run within its grant; a write waits for the owner. Restart does not duplicate the action or hide a failed result. |
| **PERSONAL-004: Agent Collaboration** | Connect an explicit useful specialist action to the existing registry/discovery/invocation infrastructure. Maintain receiver identity, scope, memory ownership and independent verification. | BullGod explains why a specialist helps, obtains required authority, delegates one supported task and reports the verified result. With no worker available, BullGod still keeps the goal and offers a useful direct next step. |

These are four milestones, not four new frameworks. Expand only after the previous
visible scenario works. The first slice may include minimal goal/approval fields
because continuity is an end-to-end product requirement; later milestones deepen
that behavior rather than postponing the first useful experience.

## First concrete end-to-end acceptance

Use a fictional project and one dedicated instance. No specialist is required.

1. Create the native `bullgod` identity and persona. The owner sees BullGod by
   name; changing the selected model preserves its ID and workspace.
2. Have a natural conversation: "Help me prepare the Cedar workshop. Keep the
   plan brief. I need a draft checklist before Friday."
3. Confirm and save that meaningful goal, linked to the owner turn rather than
   inferring a commitment from any passing mention.
4. Stop and restart only the isolated instance. Reopen the conversation.
5. Show the goal, completed planning step, pending question (venue capacity),
   next action and their source interaction/time.
6. Retrieve the relevant prior context, including the brief-plan preference.
   Demonstrate an owner correction and removal; stale values must not remain in
   active retrieval. State clearly if transcript/history retention is separate.
7. Show the actual available tools and relevant skills, with their permission
   limits. Do not claim a tool is usable solely because its name is listed.
8. Propose creating `projects/cedar/checklist.md` inside this instance's workspace.
9. Obtain explicit approval for that concrete path/content/action through an
   authenticated owner decision. Do not treat model text, a stale pending decision
   or a broad full-access mode as a one-action grant. A denial remains visible.
10. Perform the one authorized bounded write through the existing tool permission
    and filesystem boundary. An outside-workspace target must still reject.
11. Read back the resulting file through the authorized tool, retain its result
    reference and update progress exactly once. An uncertain/failing action stays
    failed or pending review; it is not silently retried after restart.
12. Explain in conversation what was done, where the checklist is, what remains
    and which decision is pending. The owner does not need logs to understand it.

Acceptance must include a new session/restart and a supported model change with
the same durable state. Deterministic fixtures prove storage/permissions; a bounded
real-model conversation proves the user experience. Neither substitutes for the
other. The current reset validates the isolated environment, not this future scenario.

## Next implementation task

**Implement PERSONAL-001 as one owner-facing continuity slice.** Start with the
existing BullGod workspace persona, native session ownership and memory API. Add
the smallest additive continuity record for `agent_id`, `session_id`, owner-stated
goal, progress, pending decision, next step, result reference and source turn/time.
Keep it in the existing conversation persistence layer; do not create another
execution journal or repurpose `recovery_tasks`.

Likely integration points are `agent/memory/conversation_store.py`,
`channel/web/api/{sessions,memory,agents}.py` and the existing chat UI under
`channel/web/static/js/chat/`. A small helper can isolate continuity operations.
Use an additive migration and existing session access checks. Owner edit/forget
must update effective retrieval and expose any separate retained audit/history.

First tests should prove two-agent separation, restart/model-change continuity,
memory correction/removal, durable pending approval, refusal before approval,
bounded write/result verification and no replay on restart. Deliver the visible
12-step scenario above before expanding goal prioritization or autonomous behavior.
If a scoped durable approval binding is missing, add only the binding required for
that one action using existing authority/intent checks; do not build a new policy
engine or reuse an unscoped UI confirmation as proof.

## Risk, compatibility and validation

- Read-only journal opening can still involve normal SQLite connection/WAL
  housekeeping; it does not promise zero filesystem metadata activity. It blocks
  application mutations and execution locks. Ownership-ignored Darwin paths fail
  closed; the supported workaround is an isolated owned data location, not changing
  APFS settings or bypassing validation.
- Discovery provider inference is kept compatible with the existing runtime.
  Fallback-enabled routes remain unknown. No model execution or selection authority
  is added, and no existing authentication or guest restriction is removed.
- The developer launcher is a macOS development tool, not a production supervisor,
  migration controller or cross-platform deployment promise. Temporary roots can
  be removed by the OS; this is not durable production storage or backup.
- Source correctness, local regression, hosted runner availability, runtime
  integration and production deployment are separate evidence layers. See
  [validation.md](validation.md). No unexecuted hosted check is marked passing.
- Legacy ingress, unobservable work and actual private-state restoration risks
  remain documented on the preserved PR branches. They are not development gates.

No live restart, private-data modification, ownership change, credential refresh,
production orchestration, merge or old-PR state change is part of this reset.
