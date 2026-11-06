# SQLite memory initialization I/O errors

## Cause found on 2026-11-06

TestPilot's live SQLite files were inside an active pCloud backup of the
external SSD's `Projects` directory. The conflict handler renamed WAL files
while SQLite still used them. A valid main database and ample free disk space
do not prevent this failure.

Evidence:

- The pCloud Back up screen showed `Projects` as **Active**. Its Exclusions
  screen did not exclude either CowAgent or CowAgent-TestData.
- TestPilot's `index [conflicted 4].db-wal` and
  `index [conflicted 5].db-wal` were created at 17:19:14 and 17:21:18 local time.
  Both times match `disk I/O error` entries in the application log.
- CowAgent uses `.cow.pid`, `index.db`, and SQLite's normal `-wal`/`-shm`
  companion paths. Its source does not generate `[conflicted]` names. The
  renamed PID files also show that the conflict handling is outside SQLite.
- A controlled test creates a WAL database, keeps its first connection open,
  renames its WAL, then constructs `MemoryStorage`. SQLite 3.45.3 on macOS
  raises `SQLITE_IOERR_SHORT_READ` (522) at `PRAGMA journal_mode=WAL`.
- An isolated copy of TestPilot's actual database initializes successfully,
  with both FTS indexes enabled and `integrity_check` returning `ok`.

The historical rename itself was not captured with a system-call trace. The
active backup configuration, matching conflict timestamps, and deterministic
SQLite reproduction establish the failure mechanism and identify pCloud as
the external conflict handler. Do not attribute these filenames to SQLite.

SQLite requires its database and companion files to remain associated. See
[SQLite's file-renaming warning](https://www.sqlite.org/howtocorrupt.html) and
[I/O result codes](https://www.sqlite.org/rescode.html).
[pCloud's guidance](https://help.pcloud.com/article/files-not-recommended-for-sync-backup-or-uploads)
also warns about conflicts on actively modified files. It states that exclusions
must be applied before backup starts; adding an exclusion to an existing backup
is not sufficient.

## Initialization and code changes

The path is `MemoryManager` → `MemoryStorage._init_db()` → `_open_conn()`:

1. Open the configured database with `sqlite3.connect`.
2. Set `PRAGMA journal_mode=WAL`, then `PRAGMA busy_timeout=5000`.
3. Probe FTS5 by creating and dropping `fts5_test`.
4. Create or migrate the memory schema and FTS tables/triggers, then commit.
5. Schedule background maintenance.

Failures now record the operation, absolute database path, SQLite extended
error code/name, and traceback. The error boundary includes schema creation
and commit, and closes a failed initialization connection.

Only a missing trigram tokenizer permits the existing capability fallback.
I/O errors propagate without removing working trigram triggers. Failure to
detach an unsupported tokenizer also propagates. WAL and indexing remain enabled.

`AgentInitializer` still reports a memory setup failure and can continue without
memory tools. A chat response or a filesystem read of `MEMORY.md` is therefore
not evidence that indexed memory works.

## Local runtime repair

The active workspace is now:

```text
/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace
```

This is outside the two active pCloud backup roots observed on this host.
The original workspace remains at:

```text
/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData/workspace
```

With CowAgent stopped and no canonical WAL present, all 29 workspace files
were copied to a new directory and verified against SHA-256 manifests. No
original database was deleted, overwritten, recovered, or rebuilt. Conflicted
companions were preserved as evidence. The model settings, roster, identity,
instructions, and memory text were retained unchanged.

Only `agent_workspace` and its matching `web_file_serve_root` changed in the
local CowAgent-TestData `config.json`. The original config and file manifest
are retained under CowAgent-Runtime. The code checkout and `COW_DATA_DIR`
location did not change.

Do not point the running service back to the old workspace after new writes:
the old copy will then be stale. Keep live databases outside file-sync and
backup conflict handlers. Use SQLite's online backup API to make consistent,
closed backup artifacts for off-device storage. Do not copy an active main
database alone, and do not remove WAL/SHM files to suppress an error.

## Verification

Run the focused regression selection from the checkout, directing test logs
to a disposable directory:

```bash
COW_DATA_DIR="$(mktemp -d)" .venv/bin/python -m pytest -q \
  tests/test_memory_storage_io.py \
  tests/test_shared_db_recovery.py \
  tests/test_memory_fts_sync.py
```

Runtime checks used TestPilot's retained indexed row, not a filesystem fact
lookup. Three fresh Python processes resolved TestPilot from the active config,
called the normal `_setup_memory_system`, registered both memory tools, and
successfully executed `memory_search` with LIKE fallback blocked. WAL, Unicode
FTS5, trigram FTS5, and integrity checks passed. Separate repeated storage
opens also passed. The shared database retained all 10 sessions, 29 messages,
and 13 runs; complete persisted table rows matched retained snapshots. All 29
original file hashes and copied non-database files remained unchanged.

No LLM/provider requests were needed. Full chat/server startup was not part of
these subsystem checks. Vector provider behavior was not exercised; this
installation already used indexed keyword search. The old conflicted files
were retained, not merged automatically.
