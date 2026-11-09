# Disposable transition and recovery

The receipt in `rehearsal.json` records fictional data only. The modeled legacy
is `90c3cd8f72ffe7a47cb20925fa538eda479317c6`, bracketed by the primary
checkout's reflog at the service's launch time; this is not loaded-source
attestation. The loaded commit is unknown. The modeled fallback is master
`f659349785acf98905901a5cc53921436a109dbc`. The candidate is PR #5 head `8d182026be2380fc574eeecd13edcffa5ed1dcb1`, with executable
source `005c1e4805c75017467b817baa2a8bbbe3f7511d`. The service runs used private storage and port 19886; their controlled
shutdowns returned zero. The intentional pre-handler initialization interruption
returned SIGTERM (-15), as separately verified by the fixture. The sandbox
denied outbound network and access to the two identified live data roots. No
provider or real task was dispatched. The initialized candidate authenticated a
one-shot request, listed three fictional identities, denied two discovery requests,
closed admission, rejected a new HTTP message, and waited for two fictional
coordinator leases to finish. These leases are not real model executions.

The legacy process stopped before the fixture file-set backup. Each fixture
SQLite database used the online backup API, and integrity checks and logical
dumps matched after restoration and fallback startup. The fixture includes three
conversations, migration markers, a memory Markdown file, one native indexed file and chunk in the global database,
one independent indexed file and chunk in each of the two per-agent memory
databases, and a completed recovery task, attempt, effect, and verification
record. All four databases were restored and their logical dumps matched. A separate SQLite WAL check confirmed that an online
backup included a committed frame and excluded an open uncommitted write. SQLite
backup alone does not coordinate multiple databases and other files: the closed
interval is essential. The receipt does not prove that the identified fixture
files cover all live state, cross-database writes, or external effects.

A separate candidate initialization was interrupted after team migration returned
and immediately before conversation migration. Candidate restart reached health;
restoring the closed-interval snapshot and running fallback again preserved the
fixture's SQLite logical dumps and memory file. This does not simulate a crash
inside a transaction or an asynchronous conversation merge. The focused
`tests/test_discovery_startup_migration.py` suite passed 2 tests, including a
fault after a committed copy and before its marker; retry retained exactly one
destination row. That fault-injection test is not a process crash. Source rollback
alone cannot reverse data migration or an external effect. Post-backup writes
would be lost by snapshot restoration and need independent reconciliation.

The initial successful drain used disabled fixture plugins and `BROWSER=true`.
A second candidate run used the observed seven enabled plugin names with only
fictional config and a fictional LinkAI placeholder. It reached health but drain
returned `plugin_runtime_untracked`, as required by the strict coordinator. The
fixture cannot establish live plugin state, actual browser behavior, or prove
absence of effects outside its isolation boundary. The constructors were reviewed
before this run: they load or write local configuration and LinkAI constructs
its client; the tested startup did not exercise message handlers.

Reproduce only on macOS with the tested venv and pinned Git commits available.
The scripts generate new fictional state and IDs in a private `mkdtemp` root;
they never use port 9899:

```sh
'/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python' docs/first-bootstrap-001/rehearsal.py
# Use the printed private root as ROOT in the following two commands.
'/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python' docs/first-bootstrap-001/recovery_fixture.py "$ROOT"
'/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python' docs/first-bootstrap-001/plugins_fixture.py "$ROOT"
```

A prior self-contained master-to-candidate-to-master run remains in the receipt
as secondary evidence; it does not attest the loaded live source. The previous
launch-baseline receipt covered only the global memory and recovery databases;
it is retained separately as two-database evidence.

The fixture creates its conversation, memory and recovery schemas with the
legacy source classes. Each run generates fresh fictional IDs. Scripts retain
private logs and receipts under the printed root. They do not execute the proposed live procedure or certify live quiescence.
