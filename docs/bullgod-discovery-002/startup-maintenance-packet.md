# DISCOVERY-002S maintenance approval packet

**Prepared for review; live execution is blocked and is not authorized.**
The startup implementation and disposable process checks are complete. All five
hosted jobs pass on the frozen candidate; the [acceptance audit](startup-acceptance.md)
records the source-specific evidence. The unresolved execution gate is an actual
admission/drain barrier for the existing PID. No supported control in that
process can establish it. The new startup observer does not solve old-process
drain and must not be presented as doing so.

## Frozen candidate and scope

- Candidate executable source: `f650268162ce5f3be9704f9c6c9f09941981ee16`.
- Startup manifest digest:
  `e7d785f25cf1a40c85b8044beb1466f9c9318bda817b08e3c44ccd64ccc0dd22`.
- Known-tested fallback: `f659349785acf98905901a5cc53921436a109dbc`.
  It is not asserted to be the code loaded by the old PID.
- Existing process: PID `28093`, start epoch `1794162129.482237`.
- Working directory: `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent`.
- Interpreter invocation:
  `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent/.venv/bin/python`.
  Process launcher markers, isolated prefix checks and `pip check` support this
  path. The framework executable must not replace it.
- Data root: `/Volumes/Predator SSD GM7 1TB/Projects/CowAgent-TestData`.
- Workspace root: `/Volumes/Predator SSD GM7 1TB/CowAgent-Runtime/workspace`.

One future approved window would preserve these paths and inherited settings,
stop only the verified old process gracefully, start this candidate once, observe
registered native identities/routes and denied/unknown selections, then verify
health and preservation. No model task, adapter contact, new enrollment, task
approval or positive-selection manufacture is in scope. The request expires in
four minutes and cannot be reused. A failed attempt requires a new explicit
decision; there is no automatic replay.

## Decisions required before the commands may run

1. **Drain — blocked.** Close admission for every configured channel and establish
   zero active turns for every registered agent, no scheduler callback/due work,
   no recovery future or unfinished verification/publication, no evolution work,
   and no external in-flight action. Recheck the barrier immediately before the
   signal. Current source has no supported aggregate control/receipt for this.
   HTTP health, quiet logs, absent scheduler files, completed persisted rows and
   a timed sleep cannot satisfy it. Do not execute the stop command on that basis.
2. **Migration — known effect, not approved.** Current global schema is compatible.
   `testpilot2`'s secondary DB has no conversation tables; startup adds only its
   missing merge marker. Fictional tests retain global rows and exercise retry
   after interrupted marker publication. If zero persistent writes are required,
   this is blocked. Otherwise the exact marker write, ordinary startup asset
   synchronization and SIGTERM's user-data save must be explicitly accepted.
   No migration, schema repair or live backup was performed here.
   Normal startup also loads config/team state, scaffolds assets, warms configured
   MCP servers and starts recovery/scheduler/evolution services. Review those
   effects for every configured agent. Any unreviewed subprocess/network action
   or resumable/due work is an abort; a read-only observer does not make the
   surrounding startup read-only.
3. **Environment — explicit private handling.** Preserve the old process's full
   environment only in an operator process's memory, never stdout, a shell command
   string, a request or an evidence file. The interpreter path is established;
   the complete old environment was not retained or reconstructed. Any refusal
   or failure to capture it is an abort. This operation needs inclusion in the
   maintenance authorization. The diagnostic credential-output incident is
   recorded in the handoff; no credential was rotated or refreshed.
4. **Rollback acceptance.** Accept the pinned fallback and the limits below. If a
   consistent data backup is required, qualify and separately authorize that
   operation before stopping the service. Source rollback cannot undo writes.
5. **Operational bounds.** Proposed bounds are 30 seconds for graceful termination
   and 60 seconds for candidate health/receipt, based on the disposable launches
   completing within those bounds. These are operator decision limits, not
   performance guarantees. Expiry causes a stop/escalation decision, never SIGKILL,
   a second instance, or an automatic retry. Agree the outage window before use.

These are specific unresolved execution conditions. The implementation is not
waiting on another discovery redesign or another repeat audit of PID 28093.

## Concrete command sequence — reference only, do not execute now

Use one private operator Python session so the environment remains in memory
through a possible rollback. The controller's installed Python is
`/usr/local/bin/python3` with psutil; the service always uses the pinned `.venv`
interpreter. The controller is not a new service or product component.

```python
from pathlib import Path
import os, signal, subprocess, psutil

repo = Path('/Volumes/Predator SSD GM7 1TB/Projects/CowAgent')
python = str(repo / '.venv/bin/python')
candidate = 'f650268162ce5f3be9704f9c6c9f09941981ee16'
fallback = 'f659349785acf98905901a5cc53921436a109dbc'
runtime_paths = ['app.py', 'config.py', 'agent', 'bridge', 'common',
                 'models', 'channel', 'plugins']
old = psutil.Process(28093)
assert old.create_time() == 1794162129.482237
assert old.cwd() == str(repo)
assert os.getuid() == os.geteuid() == old.uids().real == old.uids().effective
subprocess.run(['git', 'diff', '--exit-code', candidate, '--',
                *runtime_paths, 'scripts/discovery_startup.py'],
               cwd=repo, check=True, stdout=subprocess.DEVNULL)
# Only after the drain, private-handling and maintenance decisions above:
service_environment = old.environ()  # Never print or serialize this value.
assert psutil.Process(28093).create_time() == 1794162129.482237
assert service_environment['COW_DATA_DIR'] == str(repo.parent / 'CowAgent-TestData')
```

Create a fresh request with the exact service interpreter and preserved
settings. This complete generator uses only source metadata and strict observation
requirements; it does not initialize the runtime or read private Agent memory.
Keep the operator session open for a possible rollback. Do not execute it now.

```python
import tempfile
os.umask(0o077)
private = Path(tempfile.mkdtemp(prefix='cow-discovery002s-maintenance-', dir='/private/tmp'))
request = private / 'request.json'
log = (private / 'candidate.log').open('xb')
rollback_log = (private / 'rollback.log').open('xb')
request_program = r'''
import hashlib, json, os, sys, time, uuid
from pathlib import Path
from agent.discovery.startup_observer import PROTOCOL, source_manifest
path = Path(sys.argv[1])
now = time.time()
manifest = source_manifest()
measured = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
assert measured == 'e7d785f25cf1a40c85b8044beb1466f9c9318bda817b08e3c44ccd64ccc0dd22'
requirements = []
for target in ('testpilot', 'testpilot2'):
    requirements.append(dict(
        protocol='cow.discovery.task/1', task_id=str(uuid.uuid4()),
        policy_id='safe-default', category='analysis',
        input_contract='fictional_records.v1', output_contract='analysis_report.v1',
        persistent_memory='prohibited', persistent_context='prohibited',
        required_tools=[], max_authority=['fs.read', 'time', 'analyze_records'],
        approval='prohibited', verification='none', recovery='frozen_authority',
        cancellation='cooperative', deadline=now + 180, timeout_seconds=20.0,
        concurrency=1, permitted_mechanisms=['native_isolated'], prohibited_mechanisms=[],
        task_spec_hash=hashlib.sha256(b'native read-only startup inventory').hexdigest(),
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
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as output:
    json.dump(value, output, sort_keys=True)
    output.flush()
    os.fsync(output.fileno())
'''
subprocess.run([python, '-c', request_program, str(request)], cwd=repo,
               env=service_environment, check=True, stdout=log, stderr=log)
```

The request is mode 0600 in an owned mode-0700 directory on ownership-enforcing
storage. Its path and source digest are bound. The requirements are observation
inputs, not executed tasks. This first bounded window observes native configuration;
`bindings=[]` and `contact_authorized=False` prevent adapter observation. Separately
configured private bindings retain the existing guards. No credential is copied
into the request. Expired retained approvals stay expired.

```python
# Recheck the accepted admission/drain barrier and old process identity first.
# Validate the still-private request in the exact service interpreter without
# consuming it. Reserve the full 30s stop + 60s startup decision bounds.
pre_signal_check = r'''
import json, sys, time
from pathlib import Path
from agent.discovery.startup_observer import (
    _private_bytes, _json_pairs, _invalid_constant, _validate_request,
)
path = Path(sys.argv[1])
value = json.loads(_private_bytes(path), object_pairs_hook=_json_pairs,
                   parse_constant=_invalid_constant)
now = time.time()
_validate_request(value, now, path)
limit = min(value['expires_at'], *(item['deadline'] for item in value['requirements']))
assert limit - time.time() > 90, 'Insufficient lifetime: abort before stopping the service'
'''
subprocess.run([python, '-B', '-c', pre_signal_check, str(request)], cwd=repo,
               env=service_environment, check=True, stdout=log, stderr=log)
# If the operator pauses or conditions change, repeat this check and the drain barrier.
old = psutil.Process(28093)  # Fresh identity observation, not a cached timestamp.
assert old.create_time() == 1794162129.482237
old.send_signal(signal.SIGTERM)
old.wait(timeout=30)  # Timeout aborts; no forced kill or parallel replacement.
# Confirm port 9899 is free and the old PID/start tuple is no longer alive.
new = subprocess.Popen(
    [python, 'scripts/discovery_startup.py', '--request', str(request)],
    cwd=repo, env=service_environment, stdout=log, stderr=subprocess.STDOUT,
    start_new_session=True,
)
```

Insufficient lifetime aborts before SIGTERM. Do not extend or reuse the request;
obtain a fresh approved attempt. A passed freshness check is not a drain receipt.

Require a new actual PID/start tuple, one intended listener, health 200/ok and the
mode-0600 receipt at `<request>.receipt.json` within the agreed bound. Independently
check request hash, PID/UID, initialization epoch, source/helper/interpreter/data
bindings, registered identities, distinct routes and every `dispatch_permitted`
and `adapter_contact` flag. Missing caller/proof/capacity must remain unknown;
denials are valid. Check permitted durable metadata and report the accepted
marker/bookkeeping changes separately. A health response alone is not acceptance.

If rollback is required, retain the in-memory environment and verify the candidate
PID/start tuple. Gracefully stop only that candidate and wait for confirmed exit
and port release. Then execute the following exact source restoration and launch:

```python
if new.poll() is None:
    new.send_signal(signal.SIGTERM)
    new.wait(timeout=30)  # Abort/escalate on timeout; never force or duplicate.
# A candidate that already exited needs no signal. Verify listener release.
subprocess.run(
    ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', 'restore',
     '--source=' + fallback, '--worktree', '--', *runtime_paths],
    cwd=repo, check=True,
)
subprocess.run(['git', 'diff', '--exit-code', fallback, '--', *runtime_paths],
               cwd=repo, check=True, stdout=subprocess.DEVNULL)
restored = subprocess.Popen(
    [python, 'app.py'], cwd=repo, env=service_environment,
    stdout=rollback_log, stderr=subprocess.STDOUT, start_new_session=True,
)
```

This exact restore mechanism was exercised in a disposable Git checkout using
the real pinned commits. Candidate and fallback launches used the same working
directory, interpreter, environment and fictional data. Both reached health,
exited gracefully and preserved conversation rows and unrelated sentinel files.
The [final in-place receipt](startup-final-rehearsal.json) binds the results.

The rollback intentionally leaves runtime-path working-tree changes against the
feature-branch HEAD. Record the actual fallback hashes; do not describe HEAD as
loaded source, commit/push those rollback edits automatically, reset Git, delete
untracked files or prune recovery objects. Docs, existing worktrees, original
untracked files, approvals, profiles and live data are outside the restore path.

## Qualification and limits

The [implementation review](startup-review.md), [focused validation](startup-validation.json),
[process rehearsal](startup-rehearsal.json), [launch evidence](startup-launch-fidelity.json)
and [migration/drain assessment](startup-migration-drain.json) support this packet.
Hosted new-source validation must pass before any approval request.

Source restoration does not restore the old Python process, active work, cached
state, database changes or remote effects. The missing supported old-process drain
barrier is a genuine **no-go**. This packet supplies actual bounded commands and
known effects; it does not silently accept loss of unobserved in-flight work.
