#!/usr/bin/env python3
"""Create and manually control one private persistent BullGod on macOS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = Path(__file__).resolve().parent
if (HERE.parent / 'source').is_dir():
    sys.path.insert(0, str(HERE.parent / 'source'))
sys.path.insert(0, str(HERE))
import bullgod_dev as dev


def validate_root(path, exists=False):
    root = Path(path)
    if not root.is_absolute() or Path(os.path.abspath(root)) != root.resolve():
        raise ValueError('Root must be an absolute path without symlinks')
    parent = root if exists else root.parent
    if not parent.is_dir() or (not exists and root.exists()):
        raise ValueError('Root parent must exist and a new root must not exist')
    temp = Path(tempfile.gettempdir()).resolve()
    if root.is_relative_to(temp) or root.is_relative_to(Path('/private/tmp')) or root.is_relative_to(Path('/tmp')):
        raise ValueError('Root must not be temporary')
    probe = subprocess.run(['git', '-C', str(parent), 'rev-parse', '--show-toplevel'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if probe.returncode == 0:
        raise ValueError('Root must not be inside a Git worktree')
    device = subprocess.check_output(['df', '-P', str(parent)], text=True).splitlines()[-1].split()[0]
    volume = plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil', 'info', '-plist', device]))
    if not (volume.get('Internal') and volume.get('FilesystemType') == 'apfs'
            and volume.get('GlobalPermissionsEnabled')):
        raise ValueError('Root must be on an internal APFS volume with ownership enabled')
    if exists and (root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077):
        raise ValueError('Root must be owner-private')
    return root


def label(root, suffix):
    digest = hashlib.sha256(os.fsencode(str(root))).hexdigest()[:20]
    return f'local.bullgod.{digest}.{suffix}'


def secret_dir(root):
    return root.parent / (root.name + '-secrets')


def private_file(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
        raise ValueError('Credential file must be owner-private')
    return path.read_text().strip()


def load(root):
    root = validate_root(root, exists=True)
    info = json.loads((root / 'instance.json').read_text())
    if info.get('root') != str(root) or info.get('version') != 1 or info.get('service') != 'bullgod-live-001':
        raise ValueError('Invalid persistent instance marker')
    return root, info


def plist(root, info, suffix, args):
    return {'Label': label(root, suffix), 'ProgramArguments': [info['python'], str(root / 'launcher/bullgod_service.py'), *args],
            'WorkingDirectory': str(root), 'RunAtLoad': True, 'KeepAlive': False,
            'StandardOutPath': '/dev/null', 'StandardErrorPath': '/dev/null'}


def init(root, port, python, model_base, model, key_env, endpoints):
    if sys.platform != 'darwin':
        raise RuntimeError('macOS is required')
    root = validate_root(root)
    if not endpoints:
        raise ValueError('Select at least one exact HTTPS endpoint')
    key = os.environ.get(key_env, '')
    if not key:
        raise ValueError('Selected credential environment variable is unavailable')
    secrets = secret_dir(root)
    if secrets.exists():
        raise ValueError('Credential directory already exists')
    dev.init(port, python, model_base, model, key_env, endpoints, root=root)
    os.chmod(root, 0o700)
    secrets.mkdir(mode=0o700)
    fd = os.open(secrets / 'model-key', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(key)
    info_path = root / 'instance.json'
    info = json.loads(info_path.read_text())
    info['service'] = 'bullgod-live-001'
    info_path.write_text(json.dumps(info, indent=2))
    (root / 'launcher').mkdir(mode=0o700)
    for name in ('bullgod_service.py', 'bullgod_dev.py'):
        shutil.copyfile(HERE / name, root / 'launcher' / name)
    (root / 'launchd').mkdir(mode=0o700)
    jobs = [('app', ['run-app', str(root)])]
    jobs.extend((f'relay-{i}', ['run-relay', str(root), str(i)]) for i in range(len(info['read_relays'])))
    for suffix, args in jobs:
        with (root / 'launchd' / f'{suffix}.plist').open('wb') as stream:
            plistlib.dump(plist(root, info, suffix, args), stream)
    print(f'Created private instance: {root}')


class StartupFailure(RuntimeError):
    """A sanitized startup failure safe to present to the owner."""


def phase(root, suffix, value):
    # Overwrite one small marker per job. Values are fixed by this launcher.
    (root / 'data' / f'startup-{suffix}.phase').write_text(value)


def job_info(root, suffix):
    domain = f'gui/{os.getuid()}'
    result = subprocess.run(['/bin/launchctl', 'print', f'{domain}/{label(root, suffix)}'],
                            capture_output=True, text=True)
    if result.returncode:
        if result.returncode == 113 and 'Could not find service' in result.stderr:
            return None
        raise RuntimeError('Cannot inspect service identity')
    # Check the effective program and root before any bootout.
    if str(root / 'launcher/bullgod_service.py') not in result.stdout or str(root) not in result.stdout:
        raise RuntimeError('Service identity mismatch; no job stopped')
    def field(pattern):
        match = re.search(pattern, result.stdout, re.MULTILINE)
        return match.group(1) if match else None
    return {'pid': field(r'^\s*pid = (\d+)\s*$'),
            'state': field(r'^\s*state = ([a-z ]+)\s*$'),
            'exit': field(r'^\s*last exit code = (-?\d+)\s*$')}


def job(root, suffix, port=None):
    info = job_info(root, suffix)
    if info is None:
        return False
    if port is not None:
        if not info['pid'] or info['state'] != 'running':
            return False
        listener = subprocess.run(['/usr/sbin/lsof', '-nP', '-tiTCP:' + str(port), '-sTCP:LISTEN'],
                                  capture_output=True, text=True)
        if info['pid'] not in listener.stdout.split():
            return False
    return True


def bootstrap(root, suffix):
    subprocess.run(['/bin/launchctl', 'bootstrap', f'gui/{os.getuid()}', str(root / 'launchd' / f'{suffix}.plist')],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def stop(root, info):
    suffixes = ['app'] + [f'relay-{i}' for i in range(len(info.get('read_relays', [])))]
    present = [(s, job_info(root, s)) for s in suffixes]
    identities = [(int(details['pid']), dev.identity(int(details['pid'])))
                  for _, details in present if details and details['pid']]
    for suffix, details in present:
        if details:
            subprocess.run(['/bin/launchctl', 'bootout', f'gui/{os.getuid()}/{label(root, suffix)}'],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for pid, identity in identities:
        if identity:
            wait_for(lambda: dev.identity(pid) != identity, seconds=15)
    print('Stopped')


def healthy(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health', timeout=.5) as response:
            return response.status == 200
    except OSError:
        return False


def wait_for(check, seconds=15):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(.1)
    raise RuntimeError('Service did not become healthy; inspect the instance log')


def ready_or_failed(root, suffix, port, check):
    details = job_info(root, suffix)
    if details is None:
        raise StartupFailure(f'{suffix} disappeared during startup')
    if details['state'] != 'running' and details['exit'] is not None:
        marker = root / 'data' / f'startup-{suffix}.phase'
        value = marker.read_text() if marker.is_file() else 'not reached'
        allowed = {'sandbox preflight', 'sandbox preflight failed', 'app exec', 'relay exec'}
        if value not in allowed:
            value = 'not reached'
        raise StartupFailure(f'{suffix} exited during startup (phase: {value}; exit: {details["exit"]})')
    return job(root, suffix, port) and check(port)


def relay_ready(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=.3):
            return True
    except OSError:
        return False


def start(root, info):
    suffixes = ['app'] + [f'relay-{i}' for i in range(len(info.get('read_relays', [])))]
    if any(job(root, suffix) for suffix in suffixes):
        raise RuntimeError('Instance has loaded jobs; stop it before starting')
    for port in [info['port'], *[r['port'] for r in info.get('read_relays', [])]]:
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1', port))
    try:
        for i, relay in enumerate(info.get('read_relays', [])):
            phase(root, f'relay-{i}', 'not reached')
            bootstrap(root, f'relay-{i}')
            wait_for(lambda: ready_or_failed(root, f'relay-{i}', relay['port'], relay_ready))
        phase(root, 'app', 'not reached')
        bootstrap(root, 'app')
        wait_for(lambda: ready_or_failed(root, 'app', info['port'], healthy), seconds=30)
    except Exception:
        stop(root, info)
        raise
    print(f'Healthy: http://127.0.0.1:{info["port"]}/')


def run_app(root, info):
    phase(root, 'app', 'sandbox preflight')
    probe = subprocess.run(['/usr/bin/sandbox-exec', '-f', str(root / 'sandbox.sb'), '/usr/bin/true'],
                           env=dev.service_environment(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if probe.returncode:
        phase(root, 'app', 'sandbox preflight failed')
        raise RuntimeError('Sandbox preflight failed')
    secrets = secret_dir(root)
    if secrets.is_symlink() or secrets.stat().st_uid != os.getuid() or secrets.stat().st_mode & 0o077:
        raise ValueError('Credential directory must be owner-private')
    key = private_file(secrets / 'model-key')
    if not key:
        raise ValueError('Credential is unavailable')
    env = dev.service_environment(root)
    env['COW_LOG_MAX_BYTES'] = str(5 * 1024 * 1024)
    env['COW_LOG_BACKUPS'] = '3'
    env['BULLGOD_DEV_MODEL_KEY'] = key
    os.chdir(root / 'source')
    phase(root, 'app', 'app exec')
    os.execve('/usr/bin/sandbox-exec', ['/usr/bin/sandbox-exec', '-f', str(root / 'sandbox.sb'),
              info['python'], str(root / 'model_bootstrap.py')], env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('init')
    create.add_argument('--root', required=True)
    create.add_argument('--port', required=True, type=int)
    create.add_argument('--python', required=True)
    create.add_argument('--model-base', required=True)
    create.add_argument('--model')
    create.add_argument('--model-key-env', default='CODEX_POOLER_API_KEY')
    create.add_argument('--read-endpoint', action='append', default=[])
    for command in ('start', 'stop', 'restart', 'status', 'run-app'):
        sub.add_parser(command).add_argument('root')
    relay = sub.add_parser('run-relay')
    relay.add_argument('root')
    relay.add_argument('index', type=int)
    args = parser.parse_args()
    try:
        if args.command == 'init':
            init(args.root, args.port, args.python, args.model_base, args.model, args.model_key_env, args.read_endpoint)
            return
        root, info = load(args.root)
        if args.command == 'run-app':
            run_app(root, info)
        elif args.command == 'run-relay':
            relay = info['read_relays'][args.index]
            phase(root, f'relay-{args.index}', 'relay exec')
            os.execve(info['python'], [info['python'], str(root / 'https_relay.py'), '--listen-port',
                      str(relay['port']), '--upstream-ip', relay['address']], dev.service_environment(root))
        elif args.command == 'start':
            start(root, info)
        elif args.command == 'stop':
            stop(root, info)
        elif args.command == 'restart':
            stop(root, info)
            start(root, info)
        else:
            print(f'App loaded: {job(root, "app")}; health: {"healthy" if healthy(info["port"]) else "unavailable"}')
    except StartupFailure as exc:
        parser.exit(1, f'Error: {exc}\n')
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyError, IndexError):
        if args.command in ('run-app', 'run-relay'):
            try:
                diagnostic = Path(args.root) / 'data/startup.log'
                if diagnostic.exists() and diagnostic.stat().st_size > 16384:
                    diagnostic.unlink()
                with diagnostic.open('a') as stream:
                    stream.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")} {args.command} failed before exec; check instance configuration and permissions.\n')
            except OSError:
                pass
        parser.exit(1, 'Error: service operation failed; check instance configuration and permissions.\n')


if __name__ == '__main__':
    main()
