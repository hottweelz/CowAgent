# Architecture and PR disposition

Verified base: master `f659349785acf98905901a5cc53921436a109dbc`.
PR heads: #4 `a507a400`, #5 `8d182026`, #6 `fcbc0d25`, #7 `d6c09a25`.
All remain draft/open/unmerged. No dependency manifest changes exist in this chain.

## Existing stable product foundation — KEEP

| Responsibility | Existing implementation | Product use and limits |
| --- | --- | --- |
| Identity/personality | `agent/registry.py`; `agent/prompt/workspace.py`, `builder.py`; `bridge/agent_initializer.py` | Stable agent ID, workspace, persona/user/rule files; model configuration is separate. No new identity registry is needed. |
| Conversation/context | `agent/memory/conversation_store.py`; `agent/chat/service.py`; `channel/web/api/sessions.py` | Durable transcripts and run records, session resume/rename/delete. These do not themselves represent an ongoing owner commitment. |
| Memory | `agent/memory/{manager,storage,summarizer}.py`; `channel/web/api/memory.py` | File/index search with source/scope/path metadata. Explicit correction/forget and user-visible provenance need a coherent product flow. Avoid a second memory engine. |
| Tools and skills | `agent/tools/tool_manager.py`; `agent/skills/`; `agent/protocol/agent.py`; `channel/web/api/skills.py` | Native descriptors, skill discovery and prompt integration. Availability does not grant permission. |
| Permissions | `agent/permission/{policy,authority,filesystem}.py`; session API/UI | Read-only, workspace-write and full-access modes, registered-tool checks and file broker. UI confirmation is not a durable, scoped action approval. |
| Models | `bridge/agent_bridge.py`; `models/`; `channel/web/api/models.py` | Existing provider/model and per-session routing. Preserve agent ID/workspace/memory/goal state across model changes; do not add a second router. |
| Recovery/verification | `agent/recovery/`; `agent/external/{journal,approved_dispatch,operator_control}.py` | Durable execution attempts, intent fencing and verification. These are worker-operation records, not the owner's goal list. |
| Agent collaboration | `agent/discovery/`; `agent/subagent/`; `agent/external/` | Deterministic non-dispatching selection, restricted native delegation and authenticated persistent named invocation already exist on master. Persistent adapters currently support only their validated fictional analysis contract. |
| Communication/initiative | web channel/session/event stream; `agent/tools/scheduler/`; `agent/evolution/` | Conversation and progress delivery exist. Broad autonomy is not needed for the first experience; use explicit commitments and permitted actions before expanding initiative. |

## PR #4 — extract narrow fixes; defer the larger reader integration

| Component / actual files | Disposition | Dependency and test treatment |
| --- | --- | --- |
| `agent/external/filesystem_trust.py`; guard calls in `operator_control.py` | **KEEP** | Exact standalone Darwin ownership-enforcement guard. Modes alone cannot authenticate an ownership-ignored mount. No mount changes or new host maintenance; unavailable provenance rejects. Focused negative tests remain active. |
| Read-only opening in `agent/external/{operator_control,approved_dispatch}.py` | **KEEP** | Opens an existing journal without schema creation; SQLite read-only URI plus authorizer prevents mutation. Depends only on existing journal/schema and the guard. No approval/enrollment refresh. |
| `provider_id`/validation in `agent/discovery/contracts.py`; `_public_route`/`NativeSource._route` in `sources.py` | **KEEP / SIMPLIFY integration** | Extract only supplied-settings routing/custom-provider support. Avoid process-global settings leakage across instances. Preserve deterministic selection and existing authority; exclude new observation fields. |
| `agent/discovery/runtime_readers.py`, `private_files.py` | **DEFER** | Valuable trusted-host readers, but coupled to adapter inspection, frozen enrollment/proof, read-only audit state and native observation contracts. Leave intact on PR #4; do not replace strict provenance with an unchecked reader. |
| `agent/discovery/initialized_runtime.py`; hooks in `bridge/agent_bridge.py`, `agent/protocol/agent.py`, `agent/permission/authority.py` | **DEFER** | Genuine owner and active-reply binding are valuable for later collaboration. They add cross-module observation lifecycle and are unnecessary for PERSONAL-001. Existing execution authority remains supported on master. |
| `agent/external/inspection.py`; changes in `contract.py`, `transport.py`, `codex_adapter.py`, `cowagent_adapter.py` | **DEFER** | Signed non-dispatching inspection belongs with the trusted reader integration. Existing invocation is retained unchanged. No partial protocol extraction. |
| New Candidate observation fields in `agent/discovery/contracts.py` and `_attach` in `sources.py`; lazy exports in `__init__.py` | **DEFER** | Dependent support for the deferred readers/cold-start path; active baseline keeps its existing public contracts except provider-ID compatibility. |
| `agent/discovery/startup_observer.py`, `scripts/discovery_startup.py`, `app.py` observer wiring | **REMOVE FROM ACTIVE DEVELOPMENT** | Cold-start maintenance experiment remains preserved on PR #4. It is neither copied nor activated in the new baseline. |
| `tests/test_discovery_{in_process,runtime_acceptance,runtime_readers,startup_migration,startup_observer}.py` | **KEEP with their supported branch** | Preserve all originals. Extract only focused protection for the independent fixes into `test_bullgod_foundation.py`. Deferred feature tests remain beside their deferred implementation; no test is deleted. |

## PR #5 — defer the complete service-drain unit

`common/runtime_drain.py` and `common/service_lifecycle.py` plus the following
hooks are **DEFER** as one dependency unit. Partial hooks would produce misleading
coverage. General local development uses normal process ownership/stop behavior;
it does not claim aggregate production drain.

- Agent/chat: `agent/chat/service.py`, `agent/protocol/{agent,agent_stream}.py`,
  `agent/subagent/runner.py`, `agent/guest/runtime.py`.
- Background/storage: `agent/evolution/{executor,trigger}.py`,
  `agent/knowledge/service.py`, `agent/memory/{conversation_store,storage,summarizer}.py`,
  `agent/recovery/{runtime,service,verification}.py`.
- Tools/external: `agent/external/supervisor.py`,
  `agent/tools/bash/{background,bash}.py`, `agent/tools/browser/browser_service.py`,
  `agent/tools/scheduler/scheduler_service.py`, `agent/tools/tool_manager.py`.
- Initialization: `app.py`, `bridge/{agent_bridge,agent_initializer,bridge}.py`.
- Ingress/providers: `channel/chat_channel.py`,
  `channel/web/api/{channels,openai_compat}.py`,
  `channel/web/core/{channel,guest_pages}.py`, `channel/web/web_channel.py`,
  `models/linkai/link_ai_bot.py`, `models/xunfei/xunfei_spark_bot.py`,
  `plugins/plugin_manager.py`.

The five `tests/test_runtime_drain*.py` suites and observer changes stay with PR #5.
Its receipts and limitations remain valid only for their source/configuration.
No future personal-agent feature depends on activating this unit.

## PR #6 — completed investigation, preserved reference

**KEEP as reference**: `docs/first-bootstrap-001/` and its original handoffs.
There is no runtime implementation to integrate. Its standalone migration,
source-switch and interrupted-startup helpers are **REMOVE FROM ACTIVE DEVELOPMENT**:
retain source/history/evidence, but do not extend or make them development gates.
The documented legacy deployment concerns remain unresolved.

## PR #7 — retain the independent test fix; defer maintenance additions

| Component / files | Disposition | Treatment |
| --- | --- | --- |
| `tests/test_audio_convert.py` close-spy correction | **KEEP** | Independent test determinism fix; verifies the real handle is closed before return/error. Production audio code unchanged. |
| `common/maintenance_control.py`, `scripts/maintenance_drain.py`; observer/app/helper integration | **DEFER** | Requires the PR #4/#5 initialized-owner/drain architecture. Private one-shot control is preserved, not weakened or copied into the clean baseline. |
| `common/plugin_lifecycle.py`; `plugins/plugin_manager.py`, `plugins/cow_cli/cow_cli.py`, `plugins/linkai/midjourney.py` hooks | **DEFER** | Exact-source plugin certification is meaningful for that drain contract. It is not needed to build the personal-agent experience. Normal master plugin behavior remains intact. |
| `test_maintenance_control.py`, `test_plugin_lifecycle_bootstrap.py`, `test_bootstrap_recovery_manifest.py`, observer test changes | **KEEP with deferred feature** | Originals and fixture dependencies remain on PR #7. No supported-code protection is removed. |
| `docs/first-bootstrap-002/` reports, receipts and private-control/recovery rehearsal helpers | **KEEP reference / REMOVE helpers FROM ACTIVE DEVELOPMENT** | Completed investigation; no new controller, lifecycle cases, ownership audits or CI-runner investigation. Original branch/commits/recovery artifacts remain. |

## Non-destructive GitHub resolution

The replacement draft PR targets master directly. Review and integrate its small
extracted subset independently. PR #4 can later be split into a future collaboration
reader change and archived maintenance work; #5 stays a deferred service feature;
#6 is a completed investigation; #7 preserves deferred controls and extracted audio
test provenance. None is merged or closed by this reset.

After an explicit integration decision, a maintainer may close superseded PRs with
an explanatory comment linking the replacement and each preserved branch/report.
Closing is not deletion. Do not force-push, rebase shared history, delete branches,
discard evidence or remove security boundaries to make the chain look tidy.

The active dependency graph is simply:

```text
stable master (native personal-agent primitives + validated agent invocation)
  └─ reset integration (independent safety/routing fixes + isolated dev launcher)
      └─ PERSONAL-001 → PERSONAL-002 → PERSONAL-003 → PERSONAL-004

PR #4 → PR #5 → PR #6 → PR #7: preserved, deferred deployment/reference branch
```
