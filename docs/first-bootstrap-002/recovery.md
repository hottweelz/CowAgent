# Live-state inventory and recovery qualification

## Decision

No live private-data backup or restore was made. Actual recovery is not qualified
because no closed application-write interval or private restore has been tested.
WAL itself does not prevent SQLite online backup: all four databases use WAL,
and their sidecars and changing handle membership show why raw copying is not a
consistent substitute. A later `lsof` result with no database handles does not
prove that all connections are closed or that the service is idle.

The live metadata receipt is [live-state-manifest.json](live-state-manifest.json).
It contains only path membership, file metadata, schema names, aggregate counts,
marker keys, and SQLite sidecar sizes. It contains no database rows, prompts,
memory text, configuration values, credentials, or log values.

## Actual database set

The runtime workspace has four SQLite databases:

| Path | Role | Journal/schema | Aggregate state |
| --- | --- | --- | --- |
| `memory/long-term/index.db` | Default conversation and shared memory index | WAL, schema 64 | 13 sessions, 39 messages, 18 runs; one marker, `merged_agent:testpilot`; `testpilot2` marker absent |
| `agents/testpilot/memory/long-term/index.db` | testpilot memory index | WAL, schema 141 | 1 file row, 1 chunk row |
| `agents/testpilot2/memory/long-term/index.db` | testpilot2 memory index | WAL, schema 57 | 1 file row, 1 chunk row |
| `memory/recovery/tasks.db` | Recovery tasks, attempts, effects, and verifications | WAL, schema 7 | 2 completed tasks, 2 completed attempts, 0 effects, 2 verifications |

All four report `user_version=0`. The global DB has a separate application
migration marker table. No migration was run and no marker value was read. The
recovery counts do not prove that no work or effect is pending outside these
tables.

## Durable files and capture method

The primary data root is `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData`.
It contains `config.json`, `user_datas.pkl`, and an application `workspace/` tree.
The active workspace is `/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace`.
It contains the three identity profiles, shared and per-agent memory, recovery
history, knowledge, scheduler directories, skills/assets, system settings, and
other application workspace directories. The running source-mode plugin state
is separately located under the CowAgent checkout's `plugins/` directory. It
contains `plugins.json` and plugin-local mutable configuration/data paths. The
data root does not subsume this source-mode state.

For a future approved backup, first establish one application-level closed
interval. Use SQLite's online backup API for each database while application
writes are excluded; verify each destination with `PRAGMA integrity_check` and
compare only approved non-private continuity metadata. Then capture the related
files from all three roots as one protected filesystem set. Preserve relative
paths, modes, symlinks, and required ownership metadata. Do not copy WAL/SHM
files as a substitute for SQLite backup. Independent online backups do not make
the four databases and files a single atomic snapshot.

No complete snapshot can be created until the maintainer separately approves a
private-data copy. That approval must name source roots, private data classes,
destination, access boundary, retention/deletion rule, operator, and restore
rehearsal. The JSON configuration was parsed in process to select only the
`agent_workspace` and `appdata_dir` path fields; other values were not selected,
emitted, or hashed. `user_datas.pkl`
was not read or hashed. Do not include the application log or unrelated
operating-system files by default.

The path map now records `lstat` metadata for every entry within the three
approved roots: 64 entries in primary data, 78 in the selected workspace, and
100 in the source-mode `plugins/` directory. The manifest records each relative
path, entry type, mode, uid/gid, byte size, timestamp, and symlink target where
present. It does not contain file content or hashes. Selected path fields, profile IDs, and plugin IDs/enabled flags are listed separately; credential and other config values are not present.

The selected config has `agent_workspace` set to the active workspace path.
`appdata_dir` is absent, so CowAgent's empty default resolves it to the data
root. The saved team file lists `default`, `testpilot`, and `testpilot2`; none
has an explicit workspace path. CowAgent derives the default profile at the
workspace root and the other two at `agents/<id>/`. Their directories exist.
The duplicate `primary_data/workspace/` tree is present but is not selected by
`agent_workspace`. Keep it as a separate recovery source until its contents
are reconciled with the selected workspace; do not merge or replace either
tree automatically. The `sqlite-sync-repro-porl4k_2/` directory also exists in
primary data. Its ownership and relationship to current state are unknown, so
preserve it separately pending classification. `.DS_Store` is OS metadata.

Scheduler source paths resolve to `scheduler/tasks.json`, its `.bak`, and
`scheduler/recipients.json` at the selected workspace root. All three paths are
absent. The legacy per-agent task paths for testpilot and testpilot2 are also
absent. If present at capture time, preserve the primary task file and `.bak`
together, plus the shared recipient file in the same closed interval.

The selected shared skills directory exists and its full file inventory is in
the manifest. Per-agent skill override directories are absent, so both
secondary profiles use shared skills. The `tmp/` directory exists and contains
no files at inventory time. Source code resolves channel attachment and media
staging to this per-agent temp directory; treat it as transient, and check it
again for interrupted downloads before a transition. The LinkAI plugin may
remove an input file after it summarizes it.

The source-mode plugin tree is separate from the data root. `plugins.json`
lists nine configured plugins and seven enabled plugins. `role/roles.json` is
present; the optional `role/roles/` custom directory is absent. The Banwords
config exists, but `banwords.txt` is absent and the plugin uses an empty list
when it is missing. Godcmd has no local `config.json` (its template exists);
its temporary password is process memory, while persisted admin state belongs
to runtime config. LinkAI has no local `config.json` (its template exists).
The current plugin directory inventory is preserved separately with the exact
source selection. Plugin config values and any credentials were not read.

`.env` and `.env.local` are absent at the selected workspace, primary data,
and source roots. The source `requirements.txt`, `requirements-optional.txt`,
`pyproject.toml`, `config-template.json`, `app.py`, `.venv/bin/python`, and
`scripts/ci_test.py` have path/mode/size metadata in the manifest. Their
contents and installed dependency versions were not read. Environment values
and the service's inherited environment were not read in this inventory; the
parent harness records fresh process identity separately. Any injected
credentials are outside these filesystem snapshots.

## Fictional rehearsal

The fictional fixture is [recovery_fixture.py](recovery_fixture.py), with its
summary in [recovery.json](recovery.json). It seeds the current database schemas
through CowAgent's `ConversationStore`, `MemoryStorage`, and `TaskStore` classes.
It includes fresh fictional UUIDs, a current recovery attempt, a completed
verification, and an inert effect record. The fixture runs the real
`migrate_conversations_to_global` function against a monkeypatched in-process
registry for the candidate and fallback state.

The fixture tests SQLite backup, isolated restore, integrity, three
identity/profile continuity, conversation and recovery history, real migration
markers and archived-source behavior, migration idempotence, unknown-file
preservation, symlink and mode preservation, and missing/corrupt manifest
rejection. It adds a later user file and memory row to the failed candidate
before restore, proves restore refuses to replace that existing tree, proves the
tree is unchanged, and then explicitly reconciles those two later items into a
new fallback directory. The snapshot/restore code has no effect executor or
provider/client call path; it preserves the fictional effect row as data.

The harness requires a private 0700 root below the canonical OS temporary
directory, owned by the current user, with a fixed marker file. The snapshot
functions reject unmarked paths and destinations outside that root. Tests run
through the repository's guarded `scripts/ci_test.py`. The fixture does not run
CowAgent as candidate or fallback and is not a live backup receipt. Process
integration must use the final frozen source and the separately reserved
disposable port.

No effect is replayed. Recovery rows are preserved as history only. A source
checkout rollback returns code to a tested version; it does not undo database or
file writes. Restoring a snapshot over newer state can lose legitimate user
data. Any future restore must first compare the closed-interval manifest with
current state, reconcile later user data, and handle interrupted external work
separately. Actual private-data restoration remains untested.

The separate [real process receipt](integration.json) uses the final f59 candidate
and restored master on fictional data. All four SQLite logical digests match the
snapshots through candidate/fallback startup, and the unrelated sentinel survives.
That fixture does not create later legitimate user data; the focused recovery
fixture supplies the separate refusal/reconciliation evidence. Neither authorizes
replacing an actual live tree.

## Limits

- The active service's database-handle observations differed. Exact timestamps
  were not retained by the shell capture, so only capture order and date are
  recorded. This is transient membership evidence, not a closed-connection
  claim.
- Configuration JSON was parsed in process for the selected path fields; only
  approved path/ID/enabled metadata was retained. Profile/skill/private body
  content was not inspected. Membership is in `live-state-manifest.json`.
- Installed dependency versions and all environment variable values were not
  inspected. Fresh process environment and launch identity are parent-owned.
- OS keychain, channel/provider account state, external services, and
  system-level scheduler/network settings are outside the three roots and are
  not included in file backup. Keep them in place; any change needs separate
  authority and external-effect reconciliation.
- Pending work outside the inspected aggregate SQLite tables is unknown.
- Private snapshot consistency, cross-database transaction consistency, actual
  candidate startup, actual fallback startup, and live restore remain untested.
