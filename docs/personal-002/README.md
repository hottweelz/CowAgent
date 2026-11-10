# PERSONAL-002: persistent commitments and online follow-through

BullGod can hold several owner-confirmed commitments, check an approved news
source, retain what it has reported, track follow-ups and preserve sourced drafts.
The existing conversation provides controls and result explanations. Identity,
PERSONAL-001 memory/goal controls and supported model switching are preserved.

This branch starts at PR #9's reviewed head `adbe2105`, which was still open and
draft when checked. Its 22 final source/test hashes matched the retained receipt.
PERSONAL-002 does not merge or modify that branch. Its draft targets
`codex/bullgod-personal-001`; PRs #4–7 remain independent historical work.

## API observations

The [discovery receipt](api-discovery.json) distinguishes the host, external tool
and isolated native reader:

- Ordinary verified HTTPS GET from the host returned 200 without authentication.
  The first response was a direct array of 100 articles, 122,789 decoded bytes.
- Observed fields match the requested sample. `guid` was a string or object;
  `updatedAt` was null or text. Sixteen records had markup in headline/description/
  content. Field presence/type is an observation, not a future schema guarantee.
- A weak ETag was supplied; the conditional GET returned 304 with no body.
  No Last-Modified, advertised cache lifetime or rate-limit headers were observed.
- `limit=5` returned five articles. Bounded offset/page query observations and
  article IDs are recorded. No published pagination contract is assumed.
- System Python's default trust store failed certificate verification. The
  existing application environment's verified requests client succeeded. The
  approved reader uses the existing certifi trust bundle and verifies TLS names.
- The external web tool returned a tool-level 404; it did not supply enough
  server evidence to classify this as a confirmed endpoint HTTP response.
- The original sandbox denied public egress. The new native approved reader
  returned HTTP 200 and 100 articles inside the restricted development sandbox.
  No bot impersonation, access-control bypass or server setting change was used.
- No deliberate rate-limit stress was performed. Error, malformed-body, empty,
  redirect and rate-limit behavior is tested with controlled fixtures.

The retained [public response](api-response.json) is a point-in-time fixture.
Actual live accessibility is proved separately from fixture normalization.

## State and permissions

| Component | Native integration and boundary |
| --- | --- |
| Commitments | Additive tables in the existing ConversationStore database, scoped by native agent identity; stable IDs, revisions and real owner-turn provenance. Existing PERSONAL-001 goals are not overwritten. |
| Owner controls | Existing password-backed console authentication, same-origin JSON POST, exact enabled agent and owned conversation. Only owner controls create/edit commitments, grant reads, change priority/status/schedule, track follow-ups or save drafts. |
| HTTP reads | Exact registered `ApprovedJsonRead` and an issued immutable host context pass the native permission gateway. Ordinary agents, guests and restricted workers do not inherit this capability. Generic WebFetch and baseline capabilities are unchanged. |
| Runs and delivery | Durable unique occurrence keys and one in-flight claim per commitment. Briefing, selected/source records, report state and the native assistant message commit in one SQLite transaction. |
| Sources | All normalized seen articles are retained in execution records. Delivered selections and event keys drive coverage. Follow-ups/drafts preserve compact source snapshots even beyond the recent UI history window. |
| Recovery | Failed reads remain failed; prior owner state survives. Expired in-flight claims are uncertain and block fresh execution until the owner acknowledges them. Acknowledgment preserves the original outcome and does not claim delivery or replay its key. |
| External publication | A social draft stores text, claims and delivered source references with `awaiting_publication_approval`. There is no publish operation or external connector invocation in this milestone. |

A commitment records objective, topic preferences, priority 1–5, active/paused/
completed/cancelled status, optional cron/timezone, approved endpoint/read grant,
source conversation/turn, last attempt/success, results, pending decisions and
next action. Context reloads each owner turn and includes actual scheduling
status, current read authorization, recent sources, errors and follow-ups.
Guests, unbound runtimes and restricted workers do not receive this context.

## Retrieval and development isolation

The HTTP reader permits only configured exact HTTPS endpoints. It uses public
address pins with TLS hostname/SNI verification, revalidates at most two redirects,
forwards no credential or arbitrary headers, and caps wire/decoded bodies at
512 KiB and total execution at 20 seconds. JSON is parsed as data. Empty arrays
are valid; empty bodies or malformed schema are errors. ETag/Last-Modified,
Cache-Control freshness/no-cache/no-store and 429 Retry-After are handled without
marking failures delivered. Remote text is never an instruction or tool grant.

macOS rejected public-IP literals in sandbox network rules: that rule form
accepts only localhost or wildcard addresses. The launcher therefore starts a
small task-owned loopback TCP relay to one fixed approved public address on 443.
There is no CONNECT command, URL routing or TLS termination in the relay. TLS
hostname verification remains inside the application. The sandbox permits only
that fixed relay port, the selected local model gateway and its own web listener.
It grants no unrestricted public egress. The relay has connection/byte/deadline
bounds, receives no model credential, and stops with the isolated instance.
Same-account processes and installed runtime dependencies remain trusted.

```sh
python3 scripts/bullgod_dev.py init \
  --python '/absolute/path/to/cowagent/.venv/bin/python' \
  --model-base http://127.0.0.1:4000/backend-api/codex \
  --model gpt-6-luna \
  --read-endpoint https://tyl.ee/api/news
python3 scripts/bullgod_dev.py start /absolute/root/printed/by/init
python3 scripts/bullgod_dev.py stop /absolute/root/printed/by/init
```

The existing gateway variable must be available to `start`; its value is never
an argument or config field. The launcher initializes independent source/data/
workspace/home, a disposable console password and a separate port (19892).
Create a fresh root to reset or refresh endpoint pins. Do not copy production
profiles, private memory, OAuth files or approvals. Live CowAgent on 9899 is not
part of this procedure. Temporary roots are acceptance storage, not deployment.

## Normalization, relevance and coverage

Normalization retains IDs, URL, publisher, headline, description/content, dates,
category, region, sentiment, ranking/topic metadata and provenance/issues. Invalid
dates remain unknown with bounded original metadata. HTML/script/style markup is
reduced to plain text. A validated HTTP(S) GUID may supply the original source
when `link` is blank. A publishable selection requires a usable source URL,
publisher and headline; unsourced records are retained but cannot pad the list.

Identity aliases use source-record IDs and normalized publisher URLs; shared
`feedId` is provenance, not an article identity. Deterministic phrase qualification
uses owner preferences against article text. Metadata alone cannot qualify a
story. Explicit single-word interests are honored; multiword preferences need
multiple substantive matching terms. Relevance/follow-up priority and recency
order selection. Fewer than five qualified developments produces fewer stories.

Same-source duplicates coalesce before conservative lexical event grouping.
Related publisher reports retain distinct source links. Previous report coverage
suppresses unchanged stories, including reordered results and changed headlines.
Substantive body additions and changed numeric claims with shared context can
qualify as updates; timestamps or headline edits alone do not. Stored event keys
are retained across recognized updates. Follow-ups remain tracked independently.

This is a transparent lexical heuristic, not proof that every paraphrase is the
same event or every numeric difference is significant. It can miss synonyms or
ambiguous event relationships. The native model interprets sourced context and
explains relevance; publisher facts, sentiment and ranking remain attributed,
not independently verified. No investment recommendation is made by the fetch.

## Scheduling and recovery behavior

The existing SchedulerService and TaskStore run a typed commitment pointer,
containing identity, revision and timing rather than a new unbounded instruction.
The commitment is the source of owner intent. Pointer updates reject older
revisions under TaskStore's existing process-local lock; the executor also checks
current SQLite status, read grant and revision before fetching and delivery.
Atomic SQLite claims protect against concurrent executions and duplicate local
conversation delivery across connections/restarts.

The acceptance schedule is `0 8 * * *`, `America/New_York`. Native catch-up runs
up to ten minutes late; older missed occurrences are skipped and rescheduled.
Completed occurrence keys never deliver again. Terminal failed/uncertain slots
advance the schedule while native run history remains an error; they are not
reported as successes. An active run stays due while it finishes. Pausing,
cancelling, completion or revoked read authorization disables future work.

TaskStore itself retains its existing single-process coordination contract; this
is not a new multi-host scheduling service. The authoritative SQLite delivery
claim still rejects duplicate work. No legacy service migration is required.

## Validation and acceptance

The [plan](plan.md) maps implementation and gates. The [native receipt](native-validation.json)
and [source bindings](runtime-source.json) retain accepted phases and failures;
the [local regression receipt](local-validation.json) distinguishes final source
from interrupted and earlier passing source. Independent review findings and
closure are documented below. The [independent audit](acceptance-audit.json)
reconciles the owner journey with the native database, model metadata and source
files. The [manual procedure](acceptance.md) describes a fresh isolated replay.

| Step | Observed result and native receipt phase |
| --- | --- |
| 1 | Actual GPT-6 Luna conversation through the existing Pooler; `owner_instruction`. |
| 2 | Authenticated owner established the standing commitment; `fresh_final_commitment_after_fix`. |
| 3 | Preferred topics persisted and were recalled; `restored_context_conversation`. |
| 4 | Actual approved HTTPS retrieval supplied four fully attributed stories; `actual_live_briefing`. The separate native gateway probe also returned HTTP 200/100 articles. |
| 5 | Real model explained relevance with source URLs; `briefing_explanation`. |
| 6 | Owner requested tracking of a reported story; `followup_conversation`. |
| 7 | The owner saved the follow-up with source provenance; `followup_saved`. |
| 8 | Only the isolated process was stopped and restarted; `restart_and_model_change`. |
| 9 | Native session settings and usage record GPT-5.6 Luna; `restart_and_model_change`. |
| 10 | That model recalled the commitment, topics, prior story, follow-up and inactive schedule; `restored_context_conversation`. |
| 11 | A labeled fixture reused the retained articles; `overlap_and_material_update`. |
| 12 | Already covered stories were not selected as new; the later scheduled fixture reported no new stories. |
| 13 | A clearly fictional substantive addition was selected once as updated; `overlap_and_material_update`. It is not a real publisher development. |
| 14 | Owner changed the priority to 5; `priority_request` and `priority_saved`. |
| 15 | Priority 5 survived an owned restart; `priority_after_restart`. |
| 16 | Owner enabled daily 08:00 America/New_York; `owner_enabled_schedule`. |
| 17 | Native scheduler invoked the same authorized commitment. An actual network failure remained an error; a controlled due-time/payload case delivered and advanced the slot; `scheduled_live_failure` and `native_scheduled_delivery`. |
| 18 | Restart retained the same delivered run once and created no extra run; `restart_no_duplicate_delivery`. |
| 19 | Real model drafted from a previously reported NewsBTC infrastructure source; `social_draft_conversation`. It explicitly acknowledged the absence of a direct institutional-adoption story. |
| 20 | Owner saved text, claims and source references as awaiting publication approval; `draft_saved_not_published`. Nothing was posted. |
| 21 | Controlled network failure preserved the separate PERSONAL-001 goal, memory, preferences, follow-up and last success; `controlled_network_failure_preserves_state`. |
| 22 | Real model explained saved state, fixture versus source, unpublished draft and pause behavior; `final_owner_explanation`. |

The final model explanation required one correction: its first answer conflated
an older briefing with the final commitment and called the latest manual failure
scheduled. `initial_final_summary` preserves that answer; the correction and
response remain visible. Model prose is not the authority for execution status.
The corrected answer distinguishes the fictional update and confirms no automatic
checks while paused. [Final conversation screenshot](final-acceptance.png).

The owner paused the acceptance commitment after the checks. App, relay and
disposable browser stopped. The temporary fixture bootstrap was restored to the
original gateway-only bootstrap. All 18 native source files match the final
candidate, without asset overlays. The original live listener is still PID 28093
on 127.0.0.1:9899; no live restart, production data change or deployment occurred.

## Independent review and retained limitations

One [independent engineering review](engineering-review.json) covered native authority, HTTP confinement,
atomic delivery, scheduling and integration. Targeted follow-ups checked concrete
corrections: stale schedule revision replacement, missing model schedule context,
secondary source attribution, old source retention, explicit single-word topic
preferences, usable source URL requirements, long-article material additions and
the draft picker's earlier-source choices. The final picker excludes unreported
articles. No open source finding remains.

Earlier failed or unqualified attempts are retained. These include a startup
identity race in the owned relay, an actual record with a blank source link,
the first long-body update suppression, a picker that hid an earlier valid
source, and intermittent live read failures. Only affected interactions were
repeated with fresh run keys; completed deliveries were not replayed. The older
validation commitment was paused and retained when a fresh final commitment was
created after the attribution correction.

The scheduled success proves native scheduling with a labeled controlled
response and due time. It does not certify live morning availability. Ordinary
live fetch success is evidenced separately. Public-address pins require a fresh
isolated configuration when the provider changes addresses; the reader does not
silently select a new destination or retry another pin. A first live read can
fail within the bounded timeout and remains visible for the next owner decision.

The final local regression and hosted results are recorded separately in
[local-validation.json](local-validation.json) and
[hosted-validation.json](hosted-validation.json). Earlier passing source receipts
are retained rather than relabeled as final. Hosted availability is checked
without changing repository settings. No production deployment, multi-host
scheduler, power-cut qualification or social publishing is claimed.

The final guarded macOS/Python 3.13.1 run passed **6,152 tests and 93 subtests**,
with **36 skips**, zero failures and zero errors in 208.88 seconds. All 29
changed executable/test hashes matched before and after. Both PERSONAL-001 and
PERSONAL-002 Node UI checks passed, as did changed-Python Ruff F checks and
whitespace checks. The exact skips and nonfatal Xunfei websocket thread warning
are retained in the receipt; they are not presented as executed passing cases.

## Next capability

After review and authorized integration, PERSONAL-003 should make pending
decisions and missed/failed commitments easier to review in natural conversation,
using these existing records and permissions. Do not add a new orchestration
framework or make legacy deployment maintenance a product prerequisite.
