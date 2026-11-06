# AI handoff ledger

## 2026-11-06 17:42 EST — Codex — SQLite memory I/O repair

- Task: investigate and fix TestPilot's recurring indexed-memory startup failure.
- Branch: `fix/memory-sqlite-io`, created from the current `master` checkout.
- Team: Codex lead; Luna/high workers for conflict provenance, memory-path/test
  inspection and regression tests; one Luna/high read-only engineering review.
  The runtime accepted these model selections; effective worker model was not
  independently exposed. No HomeBoss or external worker pool used.
- Cause: live SQLite WAL files inside pCloud's active `Projects` backup were
  renamed as conflict copies. Two conflict WAL timestamps match the logged
  failures. A controlled WAL rename reproduced `SQLITE_IOERR_SHORT_READ` (522)
  at `PRAGMA journal_mode=WAL`. The historical syscall was not traced; the UI
  backup mapping, timestamp correlation, healthy isolated copies, and exact
  reproduction support the attribution. Fresh DBs worked on both APFS disks.
- Source changes: precise operation/path/SQLite-code/name/traceback diagnostics;
  full initialization error boundary and connection cleanup; propagate trigram
  I/O and cleanup errors instead of disabling indexing. WAL remains enabled.
- Host repair: copied all 29 workspace files to the previously nonexistent
  `/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace`, outside the active
  backup roots. SHA-256 checks verified the copy. Changed only `agent_workspace`
  and the matching `web_file_serve_root` in CowAgent-TestData/config.json.
  Original config and manifests are retained in CowAgent-Runtime. All original
  databases, conflicted companions, memory, history, identities and instructions
  remain intact. No production database was deleted, overwritten, or rebuilt.
- Repository files: `agent/memory/storage.py`,
  `tests/test_memory_storage_io.py`, `docs/memory-sqlite-io.md`, this ledger.
- Checks: project `.venv` Python 3.13.1 / SQLite 3.45.3; installed pytest and ruff
  only in that existing environment. `pytest -q tests/test_shared_db_recovery.py
  tests/test_memory_fts_sync.py` passed 24 tests. The worker's combined run with
  the initial new test file passed 36 tests. After adding one cleanup-error test
  and stricter operation assertions, `pytest -q tests/test_memory_storage_io.py`
  passed all 13 tests: 37 distinct focused cases passed on the final behavior.
  Test logs were routed outside production. `ruff check` on both changed Python
  files with `--select F --ignore F403,F405`, `py_compile`, and `git diff --check`
  passed. Self-review and one independent review found no blocking defect.
- Runtime results: three fresh processes called TestPilot's normal
  `_setup_memory_system` using the active config. Each registered `memory_search`
  and `memory_get`; `memory_search` returned the retained indexed row with LIKE
  fallback blocked. WAL, both FTS indexes, and integrity checks passed. Separate
  storage reopen checks passed. Complete persisted rows matched snapshots,
  including all 10 sessions, 29 messages, and 13 runs in the shared DB. All 29
  original file hashes and copied non-database file hashes remained unchanged.
- Decisions: fix the external file lifecycle through a verified runtime copy;
  do not disable WAL, delete sidecars, merge conflict WALs, or rebuild databases.
  The root pCloud backup and unrelated projects were not changed. Do not add an
  exclusion and assume it protects files already included in that backup.
- Known limits: full chat/server startup and remote embedding-provider behavior
  were not exercised. The application was stopped at entry and remains stopped;
  the actual memory setup/tool path was executed directly in fresh processes.
  No model calls were made. A short synthetic workload in the backed-up folder
  did not reproduce the intermittent pCloud event itself; deterministic WAL
  rename did. Open-connection failures can produce a precise diagnostic plus a
  second outer initialization diagnostic. The code checkout/PID location is
  still under backup; that separate operational risk was not expanded here.
- Lessons Learned:
  - Mistake: treating a healthy main database as proof that live WAL use is safe.
  - Root Cause: external conflict renames break SQLite's companion-file lifecycle;
    the old initialization message hid the exact failing operation.
  - Future Trigger: `[conflicted]` DB/WAL/SHM/PID names or recurring I/O after recovery.
  - Required Behavior Change: inspect backup coverage and record extended SQLite
    diagnostics before changing journaling, rebuilding, or moving existing data.
  - Verification Step: use an isolated WAL-rename reproduction, then verify real
    indexed retrieval across new processes and compare all retained history rows.
  - Durable Memory Update: operational findings are in `docs/memory-sqlite-io.md`.
- MEMORY.md update: not needed; no project memory file existed, and no new project
  instruction or architecture policy was introduced. Instruction files were not changed.
- Next recommended steps: run the usual CowAgent start command with the existing
  CowAgent-TestData `COW_DATA_DIR`; retain the new workspace path. Establish
  off-device backups from consistent SQLite backup artifacts. Do not revert to
  the old workspace after the new copy receives writes. Assign an upstream only
  with maintainer direction if GitHub publication is wanted.
- Next-agent notes: private receipts are in
  `CowAgent-Runtime/diagnostics/2026-11-06-memory-io/`. The original workspace is
  preserved, not an active second copy. Initial untracked `.cow [conflicted].pid`,
  `.cow [conflicted 2].pid`, and `AGENTS.md` are unrelated and must remain unstaged.
- GitHub sync blocked: GitHub remote exists but current branch has no tracked upstream.
  Intended changes are committed locally; no upstream was guessed or set.
