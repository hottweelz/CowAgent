# Candidate-specific operator procedure

**Reference only. Execution is NO-GO and is not authorized.** This replaces the
older f6502681 command packet for this milestone. It does not add a legacy drain
API or waive any new-coordinator blocker.

## Pinned inputs

| Input | Value |
| --- | --- |
| Candidate publication | `8d182026be2380fc574eeecd13edcffa5ed1dcb1` (validated PR #5 head) |
| Executable commit / tree | `005c1e4805c75017467b817baa2a8bbbe3f7511d` / `d9d8c64ef453e4e44860e2516c070258b1957b1d` |
| 368-file startup manifest | `210cece16670f2d7dc39e15eb8d2ea299388170f05f68710afd6968e7159f36f` |
| Fallback | `f659349785acf98905901a5cc53921436a109dbc` (modeled legacy, not an assertion about loaded code) |
| Existing checkout HEAD | `a507a400985512683c870ef4fe059fa5982ad13e` |
| Service invocation | `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python` |
| CWD | `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent` |
| Data / workspace | `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData` / `/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace` |
| Old identity | PID `28093`, start epoch `1794162129.482237` |
| Live / rehearsal endpoint | `127.0.0.1:9899` / `127.0.0.1:19886` |

Use the repository venv invocation, not its resolved framework executable.
Installed dependencies and executable source retain the validated PR #5 matrix.
The complete inherited environment was not exported or reconstructed. A later
operator must retain it privately in one controller process's memory, only under
separate authorization. Never print it, put it on a command line, or serialize it.
Do not substitute a minimal fixture environment for production.

## 1. Read-only preflight

Run these checks again in the authorized window. Results in this packet are
point-in-time evidence, not durable permission to signal a PID.

```python
from pathlib import Path
import os, psutil, subprocess, urllib.request, json
repo = Path('/Volumes/Predator SSD GM7 1TB/Projects/CowAgent')
python = str(repo / '.venv/bin/python')
data = repo.parent / 'CowAgent-TestData'
workspace = Path('/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace')
candidate = '8d182026be2380fc574eeecd13edcffa5ed1dcb1'
fallback = 'f659349785acf98905901a5cc53921436a109dbc'
runtime_paths = ['app.py', 'config.py', 'agent', 'bridge', 'common',
                 'models', 'channel', 'plugins', 'scripts/discovery_startup.py']
def old_identity():
    old = psutil.Process(28093)
    if (old.create_time() != 1794162129.482237 or old.cwd() != str(repo)
            or old.uids().real != os.getuid() or old.uids().effective != os.geteuid()):
        raise RuntimeError('Process identity changed; stop the procedure')
    return old
def require_python_path_set(commit):
    expected = set(subprocess.check_output(
        ['git', 'ls-tree', '-r', '--name-only', commit, '--', *runtime_paths],
        cwd=repo, text=True).splitlines())
    expected = {name for name in expected if name.endswith('.py')}
    actual = set()
    for name in runtime_paths:
        path = repo / name
        for item in (path.rglob('*.py') if path.is_dir() else [path]):
            if item.exists() and item.suffix == '.py':
                if item.is_symlink():
                    raise RuntimeError('Unexpected runtime symlink')
                actual.add(str(item.relative_to(repo)))
    if actual != expected:
        raise RuntimeError('Unexpected runtime file set; preserve and stop')
old = old_identity()
require_python_path_set('a507a400985512683c870ef4fe059fa5982ad13e')
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo,
                               text=True).strip() == 'a507a400985512683c870ef4fe059fa5982ad13e'
subprocess.run(['git', 'diff', '--exit-code'], cwd=repo, check=True,
               stdout=subprocess.DEVNULL)
subprocess.run(['git', 'diff', '--cached', '--exit-code'], cwd=repo,
               check=True, stdout=subprocess.DEVNULL)
with urllib.request.urlopen('http://127.0.0.1:9899/api/health', timeout=5) as response:
    assert response.status == 200 and json.load(response)['status'] == 'ok'
```

Also recheck configuration flags, scheduler primary/backup stores, current
recovery states and verification, all known agent workspaces, Git recovery
artifacts, original untracked files and pCloud exclusions. Do not read message or
memory bodies into diagnostic output. Do not call scheduler GET merely to inspect
state: `get_task_store()` can lazily create and migrate a store.

## 2. Admission and legacy uncertainty — current stop point

**There is no supported command that atomically closes all admission in PID
28093.** Do not insert a fabricated `drain()` call here. Individual scheduler
toggle endpoints modify persisted jobs and do not join active callbacks. Channel
stop does not settle agent futures, plugins or memory maintenance. No existing
external gateway is established in the inspected direct-loopback deployment.

A possible Class B policy would require the owner to enumerate and stop all
clients, automation, chat and manual scheduler submissions for an agreed window;
keep them excluded through fallback/acceptance; confirm no known pending work;
accept loss of unobservable in-memory work; and approve a consistent recovery
checkpoint. Zero TCP connections, terminal DB rows, and a quiet timed interval
are supporting observations only. None authenticates that exclusion or proves
quiescence. No interval duration can repair an unbounded admission path.

That policy is **not accepted or established**. Seven enabled plugins also cause
the candidate's strict coordinator to report `plugin_runtime_untracked`.
Qualification of their actual callbacks/effects is required; disabling them or
ignoring the blocker is not the remedy in this packet. Stop here today.

## 3. Preservation protocol — separate authorization required

Preserve the complete data root and all registered workspace roots, including
global/per-agent memory and conversation DBs, memory documents, team/profile and
identity files, recovery DB/locks, scheduler primary/backup/recipient stores,
knowledge, skills and other durable workspace files. Include source-mode
`plugins/plugins.json`, plugin-specific configuration/data, the current source
selection, and PID/log metadata. Existing operator authority stays at its private
location; this native-only launch has `bindings=[]` and does not consume or refresh
it. Any additional referenced path or independent writer must be resolved before
declaring the backup complete. No live backup was made by this assignment.

A pre-stop SQLite online backup can capture a consistent *single database*. It
does not capture uncommitted transactions or synchronize databases with files.
After approved graceful exit and exclusion of all other writers, take the final
closed-interval checkpoint **before candidate startup**. Use SQLite backup for
each database; include committed WAL frames, never pair a copied DB with arbitrary
old WAL/SHM files. Do not issue a live WAL checkpoint or bypass a lock.

The exact database operation qualified on fictional data is:

```python
import sqlite3
def sqlite_checkpoint(source, destination):
    # Caller has approved private storage and established the closed interval.
    # Destination must be new, inside an owned mode-0700 recovery directory.
    if destination.exists():
        raise RuntimeError('Do not overwrite a checkpoint')
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src:
        src.execute('PRAGMA query_only=ON')
        with sqlite3.connect(destination) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Checkpoint integrity failed')
    destination.chmod(0o600)
```

Copy the remaining reviewed file set only during that same closed interval,
without following unreviewed symlinks or copying DB sidecars as independent
backups. Inventory every included root, file and SQLite schema; check completeness,
integrity, identity/count/status metadata and readable restored files privately.
Use the qualified fixture restore flow as the test, not as a blanket production
backup script. The actual live state set and offline restoration remain
unqualified; authorization alone is not evidence of completeness.

Restoration must retain the failed candidate's state separately for reconciliation.
Restore into a new private destination and validate it first. Any later exchange
with live paths needs its own explicit approval and exact manifest. Never overwrite
private state, replay tasks, or silently discard post-checkpoint user work. Do not
restore an older approval journal over newer revocations or decisions.

## 4. Proposed stop and source activation

The following fragments are **not an executable authorization**. They are behind
Sections 2–3 and the independent review. A current Class C decision prohibits them.
There is no automatic force escalation, retry, or generic restart command.

```python
# NOT AUTHORIZED: execute only after the revised gate and exact effects are accepted.
import signal, socket
old = old_identity()
service_environment = old.environ()  # Memory only; never print/serialize.
assert service_environment.get('COW_DATA_DIR') == str(data)
assert service_environment.get('__PYVENV_LAUNCHER__') == python
old = old_identity()  # Fresh identity immediately before signal.
old.send_signal(signal.SIGTERM)
old.wait(timeout=30)  # Timeout stops the procedure. Never SIGKILL.

def require_free_port():
    # Avoid system-wide psutil enumeration: macOS denies unrelated process FDs.
    # Require confirmed owned-process exit before this check; do not infer it here.
    check = subprocess.run(['/usr/sbin/lsof', '-nP', '-a', '-iTCP:9899',
                            '-sTCP:LISTEN', '-t'], capture_output=True)
    if check.returncode != 1 or check.stdout or check.stderr:
        raise RuntimeError('Listener remains or ownership check is unavailable')
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', 9899))
require_free_port()
# Complete and verify Section 3 checkpoint now. Abort before any candidate start on failure.
subprocess.run(['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false',
                'restore', '--source=' + candidate, '--staged', '--worktree', '--', *runtime_paths],
               cwd=repo, check=True)
subprocess.run(['git', 'diff', '--exit-code', candidate, '--', *runtime_paths],
               cwd=repo, check=True, stdout=subprocess.DEVNULL)
require_python_path_set(candidate)
```

Both the index and worktree change for only these reviewed runtime paths. The
initial preflight requires clean tracked/index state, and original untracked files
remain outside the managed set. Preserve ignored local plugin config,
untracked files, unrelated worktrees and recovery refs. HEAD remains a source
control reference, not a claim about the files just loaded. Source selection by
`git restore --staged --worktree` is qualified from the actual primary index
(a507a400) through candidate and fallback in [source-switch-check.json](source-switch-check.json).
The earlier worktree-only sequence left two candidate-added Python files behind
because the primary index did not track them. The corrected sequence removes
these managed additions, matches the fallback Python path set and tracked bytes,
and preserves untracked and ignored sentinels. Staged runtime differences remain
against the unchanged HEAD; do not commit/push or reset them automatically.

## 5. Private request, launch and acceptance

Build a fresh request in a mode-0700 directory on ownership-enforcing local
storage, with a mode-0600 request file. The following complete program uses the
exact venv and candidate source without starting the application. Its requirements
are observation inputs, not executed tasks. It copies no environment secret into
the request. Do not reuse consumed IDs or extend an expired request.

```python
# NOT AUTHORIZED on live state: Sections 2–4 and private handling approval apply.
import tempfile
os.umask(0o077)
private = Path(tempfile.mkdtemp(prefix='cow-first-bootstrap-operator-', dir='/private/tmp'))
request = private / 'request.json'
log = (private / 'candidate.log').open('xb')
rollback_log = (private / 'fallback.log').open('xb')
request_program = r'''
import hashlib, json, os, sys, time, uuid
from pathlib import Path
from agent.discovery.startup_observer import (
    PROTOCOL, source_manifest, _private_directory, _validate_request,
)
path = Path(sys.argv[1])
_private_directory(path.parent)
now = time.time()
manifest = source_manifest()
digest = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
assert digest == '210cece16670f2d7dc39e15eb8d2ea299388170f05f68710afd6968e7159f36f'
requirements = []
for target in ('testpilot', 'testpilot2'):
    requirements.append(dict(
        protocol='cow.discovery.task/1', task_id=str(uuid.uuid4()),
        policy_id='safe-default', category='analysis',
        input_contract='fictional_records.v1', output_contract='analysis_report.v1',
        persistent_memory='prohibited', persistent_context='prohibited',
        required_tools=[], max_authority=['fs.read', 'time', 'analyze_records'],
        approval='prohibited', verification='none', recovery='frozen_authority',
        cancellation='cooperative', deadline=now + 240, timeout_seconds=20.0,
        concurrency=1, permitted_mechanisms=['native_isolated'], prohibited_mechanisms=[],
        task_spec_hash=hashlib.sha256(b'fictional no-model lifecycle observation').hexdigest(),
        requested_agent_id=target,
    ))
value = dict(
    protocol=PROTOCOL, request_id=uuid.uuid4().hex, request_path=str(path),
    issued_at=now, expires_at=now + 240, uid=os.getuid(), manifest=manifest,
    interpreter={'executable': os.path.abspath(sys.executable),
                 'prefix': os.path.abspath(sys.prefix)},
    data_root=str(Path(os.environ['COW_DATA_DIR']).resolve(strict=True)),
    contact_authorized=False, bindings=[], requirements=requirements,
)
_validate_request(value, time.time(), path)
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as output:
    json.dump(value, output, sort_keys=True)
    output.flush()
    os.fsync(output.fileno())
'''
subprocess.run([python, '-B', '-c', request_program, str(request)], cwd=repo,
    env=service_environment, check=True, stdout=log, stderr=log)
pre_launch_program = r'''
import json, sys, time
from pathlib import Path
from agent.discovery.startup_observer import (
    _private_bytes, _json_pairs, _invalid_constant, _validate_request,
)
path = Path(sys.argv[1])
value = json.loads(_private_bytes(path), object_pairs_hook=_json_pairs,
                   parse_constant=_invalid_constant)
_validate_request(value, time.time(), path)
limit = min(value['expires_at'], *(item['deadline'] for item in value['requirements']))
assert limit - time.time() > 60, 'Insufficient lifetime; do not launch'
'''
subprocess.run([python, '-B', '-c', pre_launch_program, str(request)], cwd=repo,
    env=service_environment, check=True, stdout=log, stderr=log)
```

The exact application launch shape is:

```python
# request and log are new private operator-owned files; Sections 2–4 are prerequisites.
# Validate _private_bytes + _validate_request in the same venv immediately before launch.
# Require >60 seconds remaining in both request expiry and requirement deadlines.
require_free_port()
new = subprocess.Popen([python, 'scripts/discovery_startup.py', '--request', str(request)],
    cwd=repo, env=service_environment, stdout=log, stderr=subprocess.STDOUT,
    start_new_session=True)
```

Generating the request after checkpoint/source activation avoids consuming its
short validity during backup. The observer validates again before initialization
and publication. Failure stops the attempt. Do not issue a second launch or
refresh a request automatically. A 60-second startup/health decision bound and
30-second graceful-exit bound are tested fixture bounds, not live guarantees.

Acceptance requires: the intended new PID/start owns the sole 9899 listener;
health is 200/ok; a private one-use consumed claim and receipt exist; the receipt
matches request hash, source/helper/interpreter/data root, UID/PID and initialized
runtime epoch; IDs are `default`, `testpilot`, `testpilot2`; native routes remain
unchanged; missing proof/authority is denied or unknown; every dispatch and adapter
contact flag is false. Compare the private durable metadata with the checkpoint
and account for each approved migration/asset/pickle/log change. Health alone fails
this gate.

The new coordinator is process-local and its close is monotonic. It has no public
operator route. The exact internal call is `service_lifecycle.drain(actual_owner,
timeout)`; a caller must already possess the genuine initialized owner in that
process. [driver_fixture.py](driver_fixture.py) exercises this with a parent-owned
stdin pipe in the fixture. It is not a shipped production control path. A qualified
operator invocation and enabled-plugin coverage are missing before this procedure
can promise controlled candidate drain/rollback. No source import in a separate
Python process can close the running service. Reopening requires a separately
authorized fresh process; there is no `open_admission()` operation.

## 6. Controlled fallback

Retain client exclusion. Do not kill a candidate that has admitted real work to
simulate rollback. Establish its genuine settled drain result or separately review
its interruption boundary; current enabled plugins prevent the positive result.
Verify its PID/start, signal only that owned candidate, wait for exit and require
port release. Preserve post-start state for reconciliation, then validate the
offline recovery set. Source-only restoration cannot undo data or external effects.

```python
# NOT AUTHORIZED: only after the candidate termination and data-recovery gates.
subprocess.run(['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false',
                'restore', '--source=' + fallback, '--staged', '--worktree', '--', *runtime_paths],
               cwd=repo, check=True)
subprocess.run(['git', 'diff', '--exit-code', fallback, '--', *runtime_paths],
               cwd=repo, check=True, stdout=subprocess.DEVNULL)
require_python_path_set(fallback)
require_free_port()
restored = subprocess.Popen([python, 'app.py'], cwd=repo, env=service_environment,
    stdout=rollback_log, stderr=subprocess.STDOUT, start_new_session=True)
```

Confirm fallback health, exact listener ownership and preserved approved state.
Do not reopen clients until the owner accepts the recovery result. The old Python
process, its queues, pending uncommitted transactions and external effects cannot
be recreated from Git. A request failure, timeout, missing metadata or unresolved
state ends the procedure for a new operator decision.

The listener check uses bounded `lsof` plus exact-address bind, following an
observed macOS denial of system-wide `psutil.net_connections()`. This combination
was checked on the released disposable port. No privileged enumeration or live
bind was attempted. Recheck the new process's own listener after launch; the
port check alone neither reserves it nor establishes work quiescence.
