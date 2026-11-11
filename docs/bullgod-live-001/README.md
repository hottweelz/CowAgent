# BULLGOD-LIVE-001 — persistent operational acceptance

Status: the minimum operational acceptance passed on macOS on 2026-11-10.
One genuine scheduled occurrence was observed. Sustained reliability is unverified.
The service is running independently on port 18991; the original 9899 service
was preserved. Published as [draft PR #15](https://github.com/hottweelz/CowAgent/pull/15), with no merge.

Baseline: `4f6d5a5f41161aff044cc73fc09f82c5cb187930` (`master`).
This contains PERSONAL-001 through PERSONAL-004 (PRs #9–12), backend PR #13
(`388d312d`) and desktop PR #14 (`4f6d5a5f`).

## Completed scope

1. Preserve the existing 9899 service and its checkout/state. Establish a
   separate persistent internal-APFS root and verify SQLite locking/durability.
2. Reuse the native application, sandbox, HTTPS reader and scheduler. Add only
   persistent lifecycle and transaction-consistent backup support where the
   disposable launcher and ordinary ZIP backup are insufficient.
3. Start the independent service with the existing Pooler and GPT-6 Luna.
   Save personal state and the authorized news commitment through owner UI.
4. Observe an owner-approved natural scheduled occurrence with the UI closed.
   Preserve genuine failures. Test restart, specialist approval, revocation,
   deduplication, backup/restore and the ordinary owner experience.
5. Run full local validation against deployed source; obtain one independent
   engineering review; publish a draft PR without merging.

## Initial boundaries

- Separate application port: 18991, checked free at setup; legacy port 9899
  remains unchanged.
- Data stays on internal APFS with ownership enforcement. External APFS settings
  are unchanged. Source is copied out of the development worktree before launch.
- Service jobs are manually bootstrapped with native launchd. No login startup.
  Automatic retry is disabled: explicit recovery avoids crash loops and does not
  imply replay of uncertain operations.
- Owner authentication, read-only native tool permissions, no provider fallback,
  no publication, and the exact approved news endpoint remain required.
- Private state, credentials, conversations and raw evidence stay outside Git.

## Evidence categories

Source tests, controlled fixtures, native UI/model acceptance, live HTTP,
natural scheduling, restart recovery, backup/restore and sustained reliability
are separate gates. Sustained reliability requires later observation and is
not proven by a single scheduled occurrence.

## Observed acceptance

All dates below use America/New_York; the scheduled slot was also recorded as
`2026-11-10T20:54:00Z`.

| Gate | Observed result |
| --- | --- |
| Baseline | GitHub confirms PRs #9–14 merged. The development branch starts at the stated master SHA. The original checkout and seven existing untracked files remain unchanged. |
| Legacy service | Refreshed its listener PID, executable, arguments, working directory and owner. PID, configuration digest and healthy loopback response match at closeout. No signal or state migration targeted it. Its checkout differs from master; the exact in-memory loaded version cannot be fully established from process metadata. |
| Storage | Internal APFS with ownership enabled. WAL/FULL commit, separate-process writer exclusion and reopen integrity passed. No mount or ownership policy changed. |
| Real conversation | GPT-6 Luna answered through the existing Pooler. The owner-confirmed name, news preferences and goal were saved through authenticated controls. No legacy memory was copied. |
| Live manual read | At 15:45:28, the native approved reader retrieved 100 items; two source-attributed findings were delivered at 15:45:39 with proposed follow-ups. |
| Genuine schedule | The owner explicitly approved a near-term test. The authenticated UI saved `54 15 * * *`, America/New_York. The UI/browser closed before the slot; launchd owned the service with PPID 1 and no development terminal. The normal scheduler began at 15:54:08 and delivered one new finding at 15:54:14. No callback, clock change or due-pointer edit was used. |
| HTTP evidence | The natural occurrence stored a new checked timestamp and ETag plus 100 actual feed items. Fresh-until was zero, requiring network validation. No response substitution, synthetic update or failure fixture was installed in this runtime. |
| Delivery / dedup | Reopened UI showed the scheduled result in the owner conversation. Its selected source differed from both prior delivered sources. A later separate manual check selected zero new items. Manual checks return an acknowledgement; a silent, no-change **scheduled** occurrence was tested by the existing fixtures, not observed naturally here. |
| Daily schedule | Restored through owner controls to `0 8 * * *`, America/New_York. Final enabled next occurrence: **2026-11-11 08:00 EST / 13:00 UTC**. |
| Normal restart | After work settled, stopped and started only BullGod. All captured personal, conversation, run and decision table hashes matched, integrity passed, authentication survived, and the next occurrence stayed correct. No completed delivery replayed. |
| Specialist | Native registered NewsAnalyst has a non-overlapping workspace and its own persona/model. Preparation and approval created no model run. One first execution failed verification; a new approved request completed with GPT-6 Luna, zero tools and a verified exact source excerpt. Failed/completed attempts remain separate. A denied request never ran. Repeated execution requests created no new native runs. |
| Revocation / pause | Revocation disabled Check now and the scheduler. An authenticated execution attempt returned HTTP 400; run count and fetch timestamp stayed unchanged. Pause/resume worked. Final read authorization and the daily schedule are active. |
| Model continuity | Explicit GPT-5.6 Luna selection correctly recalled the saved owner identity, preferences, schedule and specialist result without new work. The pin was cleared and GPT-6 Luna restored. No automatic provider fallback occurred. |
| Unexpected exit | One SIGKILL targeted the verified new service while no work was active. It stayed stopped for the observation interval. Explicit recovery preserved all captured personal/conversation/run table hashes and integrity; no completed occurrence or specialist action replayed. This does not certify interruption of an in-flight external effect. |
| Backup / restore | Two real snapshots and isolated inspection drills passed. The final snapshot contains 26 files and three SQLite databases: owner memory/conversations, native recovery, and specialist memory. Integrity and table counts match. Credential-value scans found neither service secret in the snapshot. Failed backup/restore preservation paths also pass focused tests. |
| UI | Owner conversation, commitment editing, attention, results, failures, approval/denial, follow-up, pause and model controls were exercised. Wide 1440×1000 and 200%-equivalent 720×500 views have no horizontal overflow, visible composer and nonzero message area; keyboard focus reaches owner controls. |
| Confinement | Unauthenticated private APIs return 401. Native permissions deny generic writes, shell, browser, send and web fetch. The live sandbox denied outside-file access, source writes, sibling-credential reads and an unapproved local network connection. No public exposure or remote-access change occurred. |

Private receipts and screenshots are retained outside Git in the application-
specific evidence directory. The [sanitized validation summary](validation.json)
and this procedure provide public technical evidence without conversation text,
credentials, databases or backups.

## Bounded integration corrections

- Route mutable plugin settings to an explicit `COW_DATA_DIR`, keeping the
  source release read-only. Ordinary source installs without the override retain
  their historical path.
- Make application log rotation opt-in for this persistent service.
- State the existing specialist verifier's one-finding-per-source, ten-finding
  and 1,000-character excerpt limits in the model contract. The first real long-
  source response exposed this omission; the failed attempt remains recorded.
- Apply the existing expanded-panel height limits at every width. The initial
  wide layout could hide the composer, although the narrow layout already passed.

No second agent framework, scheduler, registry, dispatcher or dashboard was added.

## Deployment and lifecycle

The persistent root is `~/Library/Application Support/BullGod` on internal APFS.
Its `source/` is a copied release, not a Git worktree. `config/` contains private
configuration; `data/` contains application state and bounded logs; `workspace/`
contains the native agent identity, memory, conversation database and scheduler.
`home/` and `tmp/` keep incidental runtime files inside the sandbox. The absolute
pre-existing virtual-environment interpreter is recorded in private
`instance.json`; its dependencies passed `pip check`. No model installation was
added. The source copy contains 600 runtime files, all compared with the branch.

The Pooler credential is in the separate private sibling `BullGod-secrets/`.
It is read before sandbox entry and removed from the transient environment by
the model bootstrap. The application sandbox cannot read that directory.
The console has a separate generated password in `config/config.json` (0600).
Both private directories are 0700. Secrets are excluded from the general backup.

Use the interpreter recorded in `instance.json` as `PYTHON`, and set `ROOT` to
the persistent root. These commands use the installed lifecycle copy:

```sh
"$PYTHON" "$ROOT/launcher/bullgod_service.py" start "$ROOT"
"$PYTHON" "$ROOT/launcher/bullgod_service.py" status "$ROOT"
"$PYTHON" "$ROOT/launcher/bullgod_service.py" stop "$ROOT"
"$PYTHON" "$ROOT/launcher/bullgod_service.py" restart "$ROOT"
curl --fail http://127.0.0.1:18991/api/health
```

Native launchd owns the application and the existing fixed-destination HTTPS
relay. Their plists are under `launchd/`, outside `~/Library/LaunchAgents`.
`RunAtLoad=true` starts them only when explicitly bootstrapped;
`KeepAlive=false` prevents crash loops and restart after explicit stop.
There is no boot/login installation and no second service supervisor.

Unexpected exits require explicit inspection and restart. The service does not
automatically replay uncertain actions. This deliberate manual-recovery policy
does not provide automatic crash recovery. Native SIGTERM saves legacy user
data but is not an all-agent drain protocol: stop only after current work has
settled. The command checks its launchd identity and waits for its owned process.
Application log retention is 5 MiB plus three rotated files; pre-exec diagnostics
are bounded and post-exec failures report phase/exit information.

## Owner workflow and authority

Open [BullGod](http://127.0.0.1:18991/) and sign in with the console password in
the private configuration. Reopen the existing owner conversation from History.
Personal commitments shows schedules, read grants, attributed results, attention,
follow-ups, and optional registered-specialist requests. Owner continuity shows
the saved goal and explicitly accepted facts.

The required model is GPT-6 Luna through the existing local Pooler. New unpinned
instances use the existing newest-supported-family selector. Explicit pins remain
explicit; automatic fallback is disabled. The only configured public read endpoint
is `https://tyl.ee/api/news`, with native exact-URL and public-address validation.
The owner must save the read grant through authenticated controls. The native
model has read-only tool permissions; generic shell, write, browser, send and
web-fetch capabilities are denied. This grant cannot publish or send messages.
Specialist approval is separate and permits one scoped, tool-free source review.

The news source, its articles, and model conclusions remain untrusted evidence.
Source attribution proves where a report came from; it does not establish that
publisher claims or model judgments are true. No legacy personal data was imported.

## Backup and recovery procedure

The ordinary CowAgent ZIP command copies SQLite files directly. It is unsuitable
for this live database without a consistency step. The new small helper uses
SQLite's online backup API for each database, including committed WAL content.
For a complete multi-file recovery point, first settle current work and stop only
BullGod. `--quiescent` records that operator assertion; it is not an automatic drain.

Choose a new snapshot directory under the private sibling `BullGod-Backups/`:

```sh
"$PYTHON" "$ROOT/launcher/bullgod_backup.py" backup "$ROOT" "$SNAPSHOT" --quiescent
"$PYTHON" "$ROOT/launcher/bullgod_backup.py" inspect "$SNAPSHOT"
"$PYTHON" "$ROOT/launcher/bullgod_backup.py" restore-drill "$SNAPSHOT" "$NEW_DRILL_DIRECTORY"
```

The drill destination must be new and named `bullgod-restore-*`. It receives
native state, individual consistent SQLite snapshots, identity files and scheduler
records, but no service launcher/active marker. Its configuration disables
application/channel execution and removes secrets. The helper checks integrity
and table counts without starting the application or running schedules. It never
restores over the active instance.

Pooler credentials and the console password require a separate secure source.
The snapshot preserves a sanitized inspection configuration, not a ready-to-run
deployment. Actual disaster recovery should create a new isolated runtime, map
its workspace/roster paths, restore native state while stopped, restore approved
configuration and authentication separately, inspect uncertain actions and
schedules, then explicitly start. That application-start recovery procedure is
not certified by an inspection-only drill. SQLite snapshots are individually
consistent; no cross-file atomicity or off-device backup claim is made.

## Validation, review and limits

The final Python source passed **6,376 tests**, **36 skips**, and **93 subtests**
in 219.42 seconds. The 1,366-file source/test manifests matched before and after.
Ruff's project F gate passed. There were 36 warnings, including an existing
background Xunfei TTS websocket bad-file-descriptor warning; no test failed.

Web tests passed **39/39**, desktop tests **16/16**, both owner UI checks passed,
and strict renderer TypeScript plus renderer/main builds passed. The final CSS
correction then passed the web tests, both UI checks and actual wide/narrow visual
verification. Unchanged desktop checks were retained. Build warnings concern
runtime font paths, old browser-data metadata, mixed imports and bundle size.
Local tooling was Python 3.13.1 and Node 26.8.2; no cross-platform claim is made.

[Independent engineering review](review.md) has no open actionable source finding.
At publication, implementation commit `0e201428346e213cabeb4f773319eab43c28c6c2`
returned no GitHub check runs, commit statuses, or PR workflow runs. Hosted
validation is **unverified**; empty checks are not passes. No GitHub Actions
availability investigation or workflow change was performed.

Known operational limits:

- This is one observed scheduled path, not long-term reliability certification.
  Silent no-change scheduling and injected network/model-failure paths have
  source/fixture coverage; no genuine endpoint failure or silent scheduled
  occurrence happened in this live window.
- Login startup and automatic crash restart are disabled. Start explicitly after
  login and inspect failures before restart. The retained Python environment and
  existing local Pooler must remain available. Fixed approved endpoint addresses
  need review if the service's DNS addresses change.
- A model status reply wrongly inferred that no temporary schedule was recorded
  after the daily schedule was restored. The durable occurrence and UI history
  prove the run; model summaries are not the execution ledger. The later explicit
  continuity reply correctly explained current identity, schedule and research.
- Native title generation received a Pooler HTTP 400 and used its text fallback.
  Main conversations, semantic news evaluation and the verified specialist call
  succeeded. The title failure was not converted into model-execution success.
- Existing default nested agent workspaces fail specialist isolation checks.
  NewsAnalyst was registered through the supported owner API with an explicit
  sibling workspace under this runtime's data directory; the ordinary research
  review and execution used native UI controls.
- Restart tests were performed while idle. No all-agent drain, universal
  exactly-once external effect, hostile same-UID isolation, reboot/login startup,
  off-device backup, or restored-application startup certification is claimed.

No further implementation is required for the observed minimum. Review the draft
PR before any merge. Continue normal daily use to build reliability evidence;
the next configured check is listed above.


## November 11 daily-operation follow-up

A read-only inspection on November 11 confirmed the ordinary 08:00
America/New_York occurrence in both Personal Commitments and Tasks History.
The task is labeled **Scheduled / Success**, started at **08:00:09 EST**, and
finished at **08:00:19 EST**. The saved occurrence contains 100 feed items, two
selected sourced findings and one delivery reference in the owner conversation.
Two associated follow-up proposals remain pending owner approval. The next run
is **November 12 at 08:00 EST**.

Neither selected source ID nor canonical URL repeats the three previously
reported findings. One selected item's upstream cluster ID also appears on a
different prior story, so the exact-identity check passes while the clustering
metadata has an inconsistency. The stored execution path allows an approved read
or validated cache; it does not alone establish a fresh HTTP transfer.

No manual run, schedule change, approval, restart or new model conversation was
used for this inspection. This adds one ordinary daily scheduled observation to
the November 10 near-term test; it does not certify general long-term reliability.
