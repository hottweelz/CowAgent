# BULLGOD-COMPUTER-USE-001 results

## Scope and baseline

The implementation is an isolated **fixture proof**, not a live Muse/Grok
integration. It adds deterministic acceptance tests, a native browser session
fixture, and evidence documents. No production Python, JavaScript, configuration,
permission policy, scheduler or registry is changed.

Fetched `origin/master` at `549086e80fb705c3f54037b4fff5c23465dc1490` and verified
that it contains the merged LIVE-001 / UX-001 release (`d93a65e4`, `553413c5`).
Created a separate managed worktree and `codex/bullgod-computer-use-001` branch.
The original checkout stays on `codex/bullgod-discovery-002` with its seven
pre-existing untracked files. The owner then added `customBridge-main/`; it stays
there, unchanged and outside this branch.

Neither `lsof` nor a loopback TCP connection check observed a listener on
127.0.0.1:18991 or 127.0.0.1:9899 at task start. This differs from historical
LIVE-001 evidence. No service was started, stopped, restarted or reconfigured.
Do not interpret this task as proof of service health or a current daily-news
execution. Twenty-eight existing BullGod configuration/state/launcher files and the original
checkout config template were hashed read-only; content was not printed or copied into Git.

## Demonstration

`tests/test_bullgod_computer_use.py` composes the existing `OperatorControl`,
`ApprovalJournal`, `ExternalSupervisor` and `AnalysisVerifier` with an explicitly
named deterministic test transport. It requests analysis of two fictional
records: 1,250 cents paid and -250 cents refunded. The expected net is 1,000 cents.
No real provider, app, message, purchase, post or external account is used.

The native operator journal stores exact enrollment/task decisions and submission
intent. An acknowledgement identifies a running task; it is not marked verified.
A later completion remains unverified until the existing independent verifier
reads the task-bound artifact and checks its schema, digest and computed result.
The saved journal remains authoritative across supervisor reconstruction.
Test cleanup removes disposable state afterward; no outcome is added to the
owner's live personal memory or commitment history.

The test adapter's runtime state is in process. Existing process-death/restart
regressions cover authenticated Unix-IPC runtime and host interruption. This is
not a claim that Muse or Grok exposes the same restart contract. Fixture enrollment
uses the existing legacy analysis review schema and explicit fixture metadata;
it is not evidence of a Codex enrollment or a generalized Muse/Grok enrollment.

The accepted native browser fixture uses a task-owned file page and dedicated
persistent profiles. It saves fictional local storage, closes/reopens the native
browser, checks the saved DOM state, then proves a second profile has no marker.
It also checks that a stale selector returns an error. This proves profile
persistence/separation only, not HTTP login or cookie persistence.

An earlier cookie-authenticated loopback fixture failed isolated native validation:
Python reached the fixture server, but Chrome navigation timed out after 15 seconds.
Moving the HTTP server and whole browser probe into subprocesses did not resolve
it under isolated HOME/data. A host-environment direct invocation passed, but is
excluded from acceptance. The cause of the isolation-dependent network failure is
unresolved. The failing exploratory test was replaced with the bounded local-page
proof; no application code or network permissions were changed.

## Validation ledger

| Check | Observed result |
| --- | --- |
| Existing external/approval/isolation/commitment/specialist/discovery/browser recovery selection | 238 passed in 7.17 s |
| Existing capability selection | 218 passed, 1 failed in 2.64 s due to existing test collection pollution described below |
| MCP console file in a fresh isolated process | 21 passed in 0.24 s; includes the failed case from the combined selection |
| New coordination fixture | 14 passed in 0.37 s on final source; Ruff F passed |
| Coordination plus existing approved external adapter subset | 117 passed in 17.04 s before final fixture cleanup/cancellation-observation correction; final 14-case check covers the correction |
| Native browser profile fixture | 1 passed in 5.37 s, isolated HOME/data, installed Chrome; local file storage, not HTTP authentication |
| customBridge offline checks | 7 passed; syntax check passed; no installation or connector execution |
| Independent engineering review | Complete; no actionable findings remain. Earlier HTTP server cleanup finding removed with narrower file-profile test |

The capability batch failure was
`test_mcp_handlers_read_and_write_workspace_file`: `web.storage` was absent.
`tests/test_web_history_artifacts_agent_scope.py:27-43` installs a partial `web`
module at collection when none is loaded. Its stub omits `storage`, which
`tests/test_mcp_console.py:249` requires. The complete MCP file passes separately.
No affected production code changed. Keep the two selections isolated; this
pre-existing fixture-composition issue is recorded, not represented as a green
combined run. Previously passed cases were not replayed to regenerate receipts.

### Existing regression commands

Use an existing Python environment with project dependencies. Prepare an empty
absolute token-cache directory. The repository test runner clears inherited
provider settings and redirects HOME and data into temporary directories. Its
Python socket guard does not confine native subprocess traffic.

```sh
TIKTOKEN_CACHE_DIR=/absolute/task-cache /absolute/venv/bin/python scripts/ci_test.py -q \
  tests/test_approved_dispatch.py tests/test_external_contract.py \
  tests/test_external_supervisor.py tests/test_external_runtime.py \
  tests/test_external_operator_control.py tests/test_external_analysis.py \
  tests/test_isolation_authorization.py tests/test_isolation_delegation.py \
  tests/test_personal_commitment_service.py tests/test_personal_collaboration.py \
  tests/test_personal_scheduling.py tests/test_browser_profile_identity.py \
  tests/test_browser_driver_loss.py tests/test_browser_launch_failure_cleanup.py \
  tests/test_mcp_session_recovery.py tests/test_mcp_call_failure_status.py \
  tests/test_bullgod_discovery.py tests/test_discovery_contracts.py
```

Second selection: `test_browser_snapshot_selector.py`,
`test_browser_screenshot_project_directory.py`, `test_permission_flag_driven_writes.py`,
`test_native_tool_contracts_release.py`, `test_web_history_artifacts_agent_scope.py`,
`test_desktop_macos_permissions.py`, `test_mcp_console.py`,
`test_mcp_transport_normalization.py`, `test_mcp_tool_retrieval.py`,
`test_subagent_run_records.py`, `test_subagent_parent_cancel.py`,
`test_agent_registry.py`, `test_scheduler_run_records.py`,
`test_scheduler_task_permission_mode.py`, `test_external_operator_review.py`,
`test_bullgod_foundation.py`, `test_external_api_switch.py`, all under `tests/`.
Then `scripts/ci_test.py -q tests/test_mcp_console.py` in a fresh process.

### New coordination check

```sh
TIKTOKEN_CACHE_DIR=/absolute/task-cache /absolute/venv/bin/python scripts/ci_test.py \
  tests/test_bullgod_computer_use.py
```

The 117-case subset also selected `test_codex_adapter.py`,
`test_approved_dispatch.py`, `test_external_supervisor.py`,
`test_external_analysis.py`, and `test_external_operator_control.py`.
These are fixture tests; no Codex CLI or provider was invoked. Counts from
separate commands overlap and must not be added as unique acceptance cases.
Worker command results were returned through tool output; parent batch logs
and preservation hashes were retained outside Git in a task-owned temporary
evidence directory. No raw private app data is part of this packet.

### Native profile check

The successful run used a file-backed launcher that called the existing
`scripts.ci_test.prepare_environment` with new temporary HOME/data/cache paths,
set `XDG_CONFIG_HOME` to another task-owned path, set
`COW_BROWSER_NATIVE_TEST=1`, then called
`pytest.main(['-q', 'tests/test_bullgod_browser_session_native.py'])`.
No Python socket guard was installed for this native subprocess test; the
browser visited only the task-owned file URL. The normal `scripts/ci_test.py`
runner clears the opt-in flag, so passing it only in the outer environment does
not enable this test. No browser package or plugin was installed.

## Acceptance coverage

| Requirement | Evidence |
| --- | --- |
| Denial/revocation | New composition fixture; `test_approved_dispatch.py`; `test_external_operator_control.py` |
| Missing/invalid credentials | New explicit fixture adapter selection/auth cases; `test_external_contract.py` and `test_external_runtime.py` authenticate real fixture IPC |
| Submission failure/duplicate requests | New fixture cases; external supervisor one-shot and concurrent-request regressions |
| Interruption/restart/reconciliation | New journal reconstruction; `test_external_supervisor.py` host/runtime process-death and restart cases |
| Uncertain outcomes | No automatic resubmit or adapter fallback; prior observation marked stale when contact is lost |
| Fabricated/incorrect completion | New negative verifier case; `test_external_analysis.py` schema/value/hash verification |
| Tool permission isolation | `test_isolation_authorization.py`, `test_isolation_delegation.py`, `test_native_tool_contracts_release.py` |
| Browser profile separation | New native browser fixture plus `test_browser_profile_identity.py` |
| Adapter choice/fallback | Explicit fixture-only selection rejects unimplemented real targets; existing discovery selection remains non-dispatching |
| Commitments/specialists | `test_personal_commitment_service.py`, `test_personal_scheduling.py`, `test_personal_collaboration.py`; no live schedule action |

## Real integration blockers

- **Muse:** local assistant bundle found; no verified supported external submission,
  authentication, stable task ID, status or result contract. See
  [MUSE-INTEGRATION.md](MUSE-INTEGRATION.md).
- **Grok Bot:** local Electron agent bundle and task/MCP UI code found; no verified
  inbound task interface or task lifecycle. A custom-MCP client UI does not prove
  that Grok Bot exposes an MCP server. See [GROK-BOT-INTEGRATION.md](GROK-BOT-INTEGRATION.md).
- **Desktop:** no native CowAgent generic desktop control backend. Browser support
  only covers actual browser targets. No personal browser was attached.
- **customBridge:** routing/catalog/receipt support, not an execution engine,
  approval authority or independent verifier. See
  [CUSTOMBRIDGE-ASSESSMENT.md](CUSTOMBRIDGE-ASSESSMENT.md).
- **Activation:** no real adapter, live profile, credentials or schedule was
  installed. Existing local-account operator trust is not human-presence proof.
- **Hosted CI:** not yet observed for this branch. Local tests do not imply hosted
  checks executed or passed.

## Preservation and review

[The sanitized preservation receipt](preservation.json) records 28 captured files,
zero changes, and no listeners on either service port at closeout. This covers the
BullGod config, native databases, identity/memory and schedule files captured at
start. It is not a whole-host audit or a claim that the stopped services are healthy.

One independent Luna/high engineering reviewer inspected final tests, the six
documents and the project-memory delta. No actionable finding remains. A cleanup
finding in the exploratory HTTP server fixture was resolved by removing that
fixture from the deliverable. The reviewer checked final evidence wording and
did not rerun accepted tests or access live services. A final self-review fixed
fixture cancellation revision/flag consistency and added acknowledged-observation
assertions, so retained state cannot hide a rejected response. The same reviewer
checked that correction; the final 14-case test run and Ruff F passed.

## Next step

Review the draft PR as an audit and executable fixture foundation. For a real
integration, obtain the installed target's supported task/auth/status/result
contract and an owner-approved isolated account or profile. Then implement one
bounded adapter with fresh target-specific verification. Do not enable a general
browser/desktop authority or alter the daily-news commitment to get a demonstration.
