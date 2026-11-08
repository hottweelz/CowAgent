# Temporary-index SQLite diagnostic investigation

The reproduced defect is in test cleanup. Three fixture classes in
`tests/test_shared_db_recovery.py` removed their temporary databases without
waiting for background memory maintenance. The correction changes tests only.
It does not change production connections, WAL, FTS indexing or error handling.

## Evidence and attribution

The original protected run recorded this at 2026-11-07 23:04:43 EST:

```text
operation=PRAGMA journal_mode=WAL
db_path=/var/folders/nn/3yz7zzyj617029dmpfzcvk940000gn/T/tmpq2pls42c/index.db
sqlite_errorcode=1802 sqlite_errorname=SQLITE_IOERR_FSTAT
Background maintenance ... failed: disk I/O error
```

The original log is retained under the private regression root recorded in
[regression.json](regression.json). The error occurred in `_run_maintenance`,
which opens its own connection. `MemoryStorage.close()` closes the foreground
connection; it deliberately does not wait for this asynchronous work. Existing
tests require large integrity scans and index backfills not to block opening.

All three shared-database fixture classes used `tempfile.mkdtemp()` directories
with the observed path pattern. Their teardown immediately called `rmtree`.
Two also restored logging before deletion, allowing a late background failure
to appear after the test's expected-corruption log suppression ended.

The historical log does not bind that path to a test ID, so its exact emitting
test is unknown. The source ordering, path and error support the cleanup race
as its explanation. The following experiment independently proves that race
and its exact SQLite failure; it does not retroactively add missing trace data.

## Controlled reproduction and correction

On the installed SQLite **3.45.3**, a connection subclass pauses only the
maintenance thread immediately before its real `PRAGMA journal_mode=WAL` call,
after `sqlite3.connect` has opened the file. The foreground connection closes,
then the actual fixture teardown runs. With the old teardown, it deletes the
database while the worker is paused. Releasing the worker produces real error
**1802 / SQLITE_IOERR_FSTAT** at the same pragma, without injected SQLite errors.

The new parametrized regression drove each of the three actual teardown methods.
All **three failed before the fix**, each with the same native SQLite diagnostic.
The correction calls the existing maintenance wait before removing each fixture
and before restoring its logger. It also checks thread liveness after the
existing bounded join: a timeout fails teardown and leaves the database in place.

The regression uses event barriers, not sleeps, to establish the ordering. It
checks that teardown waits while the database still exists, then releases the
worker and requires completed cleanup, no live worker and no SQLite error.
All **three pass after the fix**, including an independent reviewer run. The
focused storage-I/O, FTS and shared-history suite passes **40 tests**. This includes
WAL retention, indexed retrieval, restart persistence and conversation history.

```sh
.venv/bin/python -m pytest -q tests/test_shared_db_recovery.py \
  tests/test_memory_storage_io.py tests/test_memory_fts_sync.py --tb=short
```

The complete protected rerun and log inspection are recorded in
[merge-validation.json](merge-validation.json). Original receipts remain intact.

SQLite defines FSTAT as failure to obtain file information in the VFS layer and
warns against unlinking a database while it is in use. These sources support the
mechanism; the local reproduction supplies the application-specific evidence.
[Error definition](https://www.sqlite.org/rescode.html#ioerr_fstat),
[open-file deletion](https://www.sqlite.org/howtocorrupt.html#_unlinking_or_renaming_a_database_file_while_in_use).

## Scope and remaining limits

This diagnostic differs from the earlier renamed-WAL reproduction, which reports
`SQLITE_IOERR_SHORT_READ` (522). It does not establish who created historical
`[conflicted]` filenames or show a new production-memory failure. No production
database, memory, history, native authentication or configuration was accessed
or modified. Genuine initialization errors still propagate with their diagnostic
details; no error fallback, logging filter or database rebuild was added.
