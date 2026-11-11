# BULLGOD-UX-001 — conversation space and instance identity

Scope: correct the two owner panels that dominated the live BullGod chat. Keep
PERSONAL-001 through PERSONAL-004 state, approvals, execution and permission
boundaries intact. This follow-up to LIVE-001 is included in PR #15, merged into
`master` on 2026-11-11 at the maintainer's request.

## Design and acceptance

- A compact, wrapping management row replaces the two large inline cards.
  Both editors start closed when no preference exists. Header status comes from
  current saved records, and each header opens its existing editor in a dialog.
- Open/closed preferences are local to the browser and agent. Reload and chat
  navigation retain them. Native dialog focus, Close and Escape keep keyboard
  navigation usable. An editor does not permanently reduce conversation height.
- The existing `default_agent_name` supplies the tab, sidebar, sign-in and welcome
  identity. Unnamed instances retain CowAgent; non-agent mode retains AI Assistant.
  Names are escaped as text. No new branding configuration or agent routing exists.
- The running 18991 source receives the verified correction. No legacy 9899 source,
  process, configuration, memory, scheduler or approvals are changed.

QA inventory: fresh default state; each open/close cycle; Escape and focus return;
open and closed state across reload/navigation; visible current status and stale
fetch handling; existing goal, memory, approval, specialist and commitment controls;
normal and 200%-equivalent viewports; title/sidebar/sign-in/new-chat identity;
source equality, health and durable-state preservation after deployment.

## Workspace-read investigation

The screenshot response was broader than the actual permission policy. Read-only
mode permits ordinary `read`, `ls` and `search_files` operations inside the granted
workspace. Its restricted `FileBroker` excludes internal state, including
`knowledge/`, memory, credentials and agent configuration. The authenticated Files
browser uses a separate `WorkspaceService` and system-asset route.

This instance has knowledge indexing disabled and no `knowledge/` directory or
`knowledge/index.md`. The retained authorization log does not show a file-tool
call for the reported question, so a specific rejected tool call is not proven.
No permission or knowledge setting was changed. Enabling knowledge access would
require a separate, explicit change to that policy and deployment configuration.

Source references: `agent/permission/policy.py`, `agent/permission/filesystem.py`,
`agent/prompt/builder.py`, `channel/web/api/workspace.py` and the existing launcher
configuration in `scripts/bullgod_dev.py`.

## Verification

Implemented and deployed on 2026-11-10 from `codex/bullgod-live-001`.
[PR #15](https://github.com/hottweelz/CowAgent/pull/15) was finalized and merged
on 2026-11-11 as `d93a65e427bd56b556c5524ffaa90103a2068a7b`.
The merge did not restart or migrate either running service.

| Check | Result |
| --- | --- |
| Branding and asset wiring | 17 focused Python tests passed; configured-name escaping and legacy fallback covered. |
| Existing web regression | 39 tests passed. |
| Personal and commitment UI | Both existing behavioral checkers passed, including request fencing, approval controls, state preferences and status counts. |
| Syntax and lint | Changed JavaScript syntax and Python Ruff F checks passed. |
| Native controls | Both panels start closed; each opens with one click. Open state survives reload. Closed state survives reload/navigation. Enter, Escape, focus return and native focus containment passed. |
| Authentication | A remembered open dialog does not cover sign-in; it restores after successful sign-in. |
| Responsive UI | 1920x1000, 1440x1000 and 720x500 viewports inspected. No horizontal overflow. Both dialogs scroll within the viewport; Close remains accessible. The 720x500 run is a 200%-equivalent layout check, not a cross-browser zoom certification. |
| Conversation space | With history and Files open at 1440x1000, chat width is 592 px, the controls use 38.8 px, and messages retain 770.2 px. The composer ends at y=941. Previous panels used roughly 493 px at the 1000 px test height. |
| Existing editors | Goal/memory and commitment forms, read grants, source records and specialist review controls remain in their original event/API paths. No action, grant change, new model run or replay was triggered for UI bookkeeping. |
| Deployment | 12 changed runtime files match this branch. Fourteen captured owner/specialist state tables and the runtime configuration are unchanged; SQLite integrity passed. Both 18991 and legacy 9899 return HTTP 200; the legacy PID and config digest are unchanged. |
| Independent review | Luna reviewed the branding/escaping/default-name changes: no actionable finding. Parent reviewed and exercised the panel changes. |

Screenshots, rollback copies, state hashes and detailed receipts are private and
outside Git under the application's UX evidence directory. The browser test
session is intentionally left available for inspection. Refresh an existing
BullGod browser tab to load the new assets.

The full LIVE-001 Python/desktop evidence remains historical evidence for that
implementation. This correction ran focused web/branding checks; it did not
repeat 6,376 Python cases or certify unchanged desktop builds again. Hosted
validation remains unverified; the prior checks were empty, not passes.

Known limits: panel preferences belong to this browser and agent, not to the
server account. Clearing browser storage resets them. The dialogs use native
browser support. The knowledge-policy finding above remains separate from this
UI correction. Normal daily operation is still needed for sustained-reliability
evidence.
