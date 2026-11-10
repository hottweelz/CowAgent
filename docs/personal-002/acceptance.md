# Reproduce the PERSONAL-002 owner experience

Use a fresh isolated root from the launch procedure in [README.md](README.md).
Use the existing runtime-injected Pooler gateway and GPT-6 Luna. Do not copy
production profiles, memory, approvals or OAuth files. Port 9899 is excluded.
Keep the root between restarts; creating a new root resets the test identity.

1. Open the printed console URL and sign in using its disposable password.
   Start a BullGod conversation. State the standing news instruction and topics
   from the task. Ask for a concise explanation of the intended responsibility.
2. Expand **Personal commitments**. Review the objective, topic preferences,
   priority, endpoint and read grant. Save the commitment from the actual owner
   turn. Leave its schedule disabled initially. Save a second commitment and a
   separate PERSONAL-001 goal/fact to check that the records do not overwrite.
3. Choose **Check now**. Inspect the delivered briefing, publisher URLs, dates,
   new/updated labels and relevance explanation. Fewer than five stories is valid
   when fewer qualify. A failed read must remain an error; it is not a briefing.
4. Ask BullGod to explain the source-backed developments. Request one follow-up.
   Save the follow-up from that owner turn using a reported source in the card.
5. Stop and start only this isolated root. Reopen the conversation. Select a
   supported second model through the native model picker; acceptance used
   GPT-5.6 Luna. Ask it to recall the commitment, preferences, prior briefing,
   follow-up and whether the schedule is enabled.
6. Change the priority to 5 through the owner controls. Restart the same isolated
   root and confirm the priority and previous records remain.
7. Explicitly enable `0 8 * * *` with `America/New_York`. Check the next run time.
   The native scheduler invokes the stored commitment; no extra read approval is
   needed. Check failed and delivered run states separately. Restart after a
   delivery and verify its occurrence is present once with no extra delivery.
8. Ask for a short LinkedIn draft using a reported institutional-adoption source,
   or the closest relevant infrastructure source if none exists. Require that
   limitation to be explicit. Save the model's text, source and claims through
   the card. Sources from earlier reports remain selectable. Confirm its state
   is **awaiting publication approval**. This milestone has no publishing path.
9. Ask for a concise status explanation grounded in saved records. Pause the
   commitment and confirm it has no next scheduled run. Stop the isolated root
   and disposable browser. Preserve receipts and the root for inspection.

## Deterministic cases and evidence boundaries

The actual feed changes. Do not require a real publisher to create a material
update during a test. The retained native journey used the public response and
an explicitly fictional addition to one article for overlap/update cases.
The native receipt labels the injected response; the modified fixture remains
in the owned temporary root as `acceptance-news.json`.

For those controlled cases, the task bootstrap substituted only the approved
fetch result and added a fixture label to the rendered briefing. It did not
replace the native commitment store, scheduler, permission code, model router,
conversation DB or UI. The scheduler's due timestamp was advanced for the test;
the configured cron, timezone and owner grant were retained. A separate mode
returned a controlled network error. The original bootstrap was restored after
cleanup. These fixtures do not prove endpoint accessibility; the actual native
HTTPS 200 and real sourced briefing supply that evidence separately.

Executable, bounded equivalents for schema/error/overlap/material updates,
concurrency, restart/no replay and schedule behavior are in:

```sh
TIKTOKEN_CACHE_DIR=/absolute/prepared/cache /absolute/venv/bin/python \
  scripts/ci_test.py tests/test_personal_articles.py \
  tests/test_personal_commitments.py tests/test_personal_commitment_service.py \
  tests/test_personal_scheduling.py tests/test_personal_http.py -q
node tools/check-commitments-ui.mjs
```

The acceptance audit checks the native database read-only against conversation
turns, model usage, deliveries, draft provenance and the final source manifest.
Preserve rejected/unqualified attempts and correct model statements visibly.
Do not repeat valid real interactions merely to regenerate evidence.
