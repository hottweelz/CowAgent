# Reproduce the owner experience

Use the existing isolated launcher from the candidate checkout. Keep the root
between restarts. A new root resets the test identity and data. Do not use the
production service, profile, memory, approvals or OAuth files.

```sh
python3 scripts/bullgod_dev.py init --port 19893 \
  --python '/absolute/path/to/CowAgent/.venv/bin/python' \
  --model-base http://127.0.0.1:4000/backend-api/codex \
  --model gpt-6-luna --read-endpoint https://tyl.ee/api/news
python3 scripts/bullgod_dev.py start /absolute/printed/root
```

The existing Pooler gateway environment variable must be available at start.
Do not echo it, put it in arguments/config, or copy upstream OAuth credentials.
The launcher prints the disposable console password's path, not its value.
It retains the existing default-deny sandbox and fixed approved-read relay.

1. Sign in at the printed URL. Start a BullGod conversation and state the
   standing digital-assets/institutional-adoption/regulation/fintech instruction.
2. In **Personal commitments**, review and save the objective and preferences
   from that persisted owner turn. Set morning cron `0 8 * * *` and timezone
   `America/New_York`; explicitly enable schedule, read authorization and
   semantic initiative. Review exact endpoint, expiry/until-revoked and minimum
   interval. Retain a separate personal goal/fact to check preservation.
3. Close the owner conversation. Wait for the next due time, or in this owned
   fixture only use native TaskStore to set the typed commitment pointer's
   `next_run_at` to now. Do not call Check now or send another owner prompt.
   Observe the existing scheduler's new occurrence and actual approved fetch.
4. Reopen the same conversation. Ask what needs attention. Compare the answer
   with the card's actual check, attributed sources and pending decision.
5. Ask for a short source-attributed social draft. Save its exact text, claims
   and delivered source in the card; choose **Request publication approval**.
   Inspect the immutable proposal. Do not publish.
6. Stop/start only the owned root and select GPT-5.6 Luna in the native model
   picker. Confirm commitment, sources, pending decision and grant survived.
   Deny publication through its owner control; no external effect may follow.
7. For overlap, inject only the previously delivered source as a labeled
   approved-reader response fixture and advance the owned native due pointer.
   Expect a completed check with no new assistant message or duplicate decision.
8. For update, add clearly fictional material body facts to that source, label
   the briefing **CONTROLLED ACCEPTANCE FIXTURE**, and run a fresh due occurrence.
   Real model interpretation can produce a new relevant finding. Keep this
   separate from actual network evidence. Dismiss a finding and inspect history.
9. Revoke the grant through the owner control. A controlled due callback must
   make no fetch and create no new commitment run. Restore its pointer disabled.
10. Inject a conversation response timeout before the provider call. Verify the
    native run is failed, not successful, and owner state/deliveries are unchanged.
    Remove the fault and ask for current status. Include all recent checks in
    chronological order when distinguishing earlier delivery from later fixtures.
11. At 200% effective zoom, expand commitments and use the keyboard to reach
    review controls. Verify readable labels, panel scrolling, no horizontal
    overflow, nonzero chat height and visible input/send controls.
12. Stop the owned instance/browser, restore the original bootstrap, preserve
    all fixtures and failed attempts, and compare final runtime source bytes.

The retained journey used a small task-bootstrap substitution for fetch/failure
cases and native TaskStore due-time adjustment. Registry, store, model route,
owner controls and scheduler were not replaced. These instructions do not grant
permission to renew an existing expired or revoked approval.

Focused automated equivalents (guarded, no real providers):

```sh
TIKTOKEN_CACHE_DIR=/absolute/prepared/cache /absolute/venv/bin/python \
  scripts/ci_test.py tests/test_personal_initiative_store.py \
  tests/test_personal_interpretation.py tests/test_personal_commitment_service.py \
  tests/test_personal_context.py tests/test_personal_scheduling.py -q
node tools/check-commitments-ui.mjs
node tools/check-personal-ui.mjs
```

Full regression uses the same wrapper with directory-mode `tests/ -q` and the
selected virtual environment first on PATH. Preserve source hashes before/after,
JUnit and platform skips. The [audit](acceptance-audit.json) maps the original
specification's exact 28 steps; the grouped instructions above do not renumber it.
