#!/usr/bin/env python3
"""Start a disposable, sandboxed CowAgent development instance on macOS."""
import argparse
import json
import ipaddress
import os
from pathlib import Path
import secrets
import select
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit

REPO = Path(__file__).resolve().parent.parent


def model_endpoint(base):
    """A deliberately selected local gateway; no arbitrary outbound grant."""
    url = urlsplit(base)
    if (url.scheme != 'http' or url.hostname != '127.0.0.1' or url.username
            or url.password or url.query or url.fragment or not url.port
            or url.port == 9899 or not 1024 <= url.port <= 65535
            or any(c not in '/abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in url.path)):
        raise ValueError('Model base must be an explicit http://127.0.0.1:port/path gateway other than 9899')
    return url.port


def approved_endpoint(url):
    """Resolve an explicit HTTPS read endpoint before entering the sandbox."""
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
            or parsed.password or parsed.fragment or parsed.query
            or parsed.port not in (None, 443) or not parsed.path
            or parsed.netloc != parsed.hostname):
        raise ValueError('Select an exact HTTPS hostname/path without credentials or query')
    addresses = sorted({row[4][0] for row in socket.getaddrinfo(
        parsed.hostname, 443, socket.AF_INET, socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError('Approved endpoint must resolve only to public addresses')
    return addresses


MODEL_BOOTSTRAP = '''"""Task-owned model bootstrap; the credential stays only in memory."""
import os
from pathlib import Path
import json
import runpy
import sys
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / 'source'))
credential = os.environ.pop('BULLGOD_DEV_MODEL_KEY', '')
base = json.loads((root / 'instance.json').read_text())['model_base'].rstrip('/')
from models.openai.openai_http_client import OpenAIHTTPClient
original_headers = OpenAIHTTPClient._build_headers
def gateway_headers(self, api_key, extra_headers, url=None):
    headers = original_headers(self, api_key, extra_headers, url)
    if url and url.startswith(base + '/'):
        headers['Authorization'] = 'Bearer ' + credential
    return headers
OpenAIHTTPClient._build_headers = gateway_headers
runpy.run_path(str(root / 'source/app.py'), run_name='__main__')
'''


def resolve_python(interpreter):
    path = Path(interpreter)
    if not path.is_absolute() or not path.is_file():
        raise ValueError('Select an absolute Python interpreter path')
    path = Path(os.path.abspath(path))
    probe = subprocess.run(
        [str(path), '-I', '-c', 'import json,sys; print(json.dumps([sys.prefix,sys.base_prefix]))'],
        env={'HOME': '/var/empty', 'PATH': '/usr/bin:/bin', 'LANG': 'en_US.UTF-8'},
        capture_output=True, text=True, check=True, timeout=10)
    prefix, base = (Path(value).resolve() for value in json.loads(probe.stdout))
    framework = Path('/Library/Frameworks/Python.framework').resolve()
    if (prefix == base or not (prefix / 'pyvenv.cfg').is_file()
            or not (prefix / 'lib').is_dir() or path.parent.resolve() != (prefix / 'bin').resolve()
            or not path.resolve().is_relative_to(framework) or not base.is_relative_to(framework)):
        raise ValueError('Select a virtual environment backed by a macOS Python.framework interpreter')
    return str(path), prefix, framework


def service_environment(root):
    return {'HOME': str(root / 'home'), 'TMPDIR': str(root / 'tmp'), 'COW_DATA_DIR': str(root / 'data'),
            'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8',
            'PYTHONDONTWRITEBYTECODE': '1', 'BROWSER': 'true'}


def quoted(path):
    return json.dumps(str(path))


def identity(pid):
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'lstart=', '-o', 'command='], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ''


def load(root):
    root = Path(root).resolve(strict=True)
    base = Path(tempfile.gettempdir()).resolve()
    if root.parent != base or not root.name.startswith('bullgod-dev-') or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError('Instance root must be an owner-private bullgod-dev directory in the system temporary directory')
    info = json.loads((root / 'instance.json').read_text())
    if info.get('root') != str(root) or info.get('version') != 1:
        raise ValueError('Invalid instance marker')
    return root, info


def init(port, interpreter, model_base=None, model=None, key_env='CODEX_POOLER_API_KEY', read_endpoints=()):
    if sys.platform != 'darwin' or not Path('/usr/bin/sandbox-exec').exists():
        raise RuntimeError('macOS sandbox-exec is required')
    if port == 9899 or not 1024 <= port <= 65535:
        raise ValueError('Use a non-privileged port other than 9899')
    if bool(model_base) != bool(model):
        raise ValueError('Select both --model-base and --model')
    model_port = model_endpoint(model_base) if model_base else None
    if model_port == port:
        raise ValueError('The model gateway and console must use different ports')
    if not key_env or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for c in key_env):
        raise ValueError('Use an uppercase environment variable name for the model key')
    python, prefix, framework = resolve_python(interpreter)
    endpoints = {url: approved_endpoint(url) for url in read_endpoints}
    relays = {}
    reserved = []
    try:
        for url in endpoints:
            sock = socket.socket()
            sock.bind(('127.0.0.1', 0))
            reserved.append(sock)
            relays[url] = sock.getsockname()[1]
    finally:
        for sock in reserved:
            sock.close()
    root = Path(tempfile.mkdtemp(prefix='bullgod-dev-')).resolve()
    source = root / 'source'
    source.mkdir()
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=REPO).split(b'\0')
    for name in tracked:
        if not name:
            continue
        rel = Path(os.fsdecode(name))
        src = REPO / rel
        allowed = {'agent', 'bridge', 'channel', 'cli', 'common', 'models', 'plugins', 'skills', 'translate', 'voice'}
        if (rel.parts[0] not in allowed and str(rel) not in {'app.py', 'config.py', 'config-template.json'}):
            continue
        if src.is_symlink() or not src.is_file() or rel.name in ('config.json',):
            continue
        dest = source / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    for name in ('data', 'workspace', 'home', 'tmp'):
        (root / name).mkdir(mode=0o700)
    (root / 'workspace/AGENT.md').write_text(
        '# BullGod\n\nYou are BullGod, the owner\'s persistent personal AI agent. '
        'Your identity and commitments are independent of the selected model. '
        'Speak naturally and concisely. Help the owner remember what matters, '
        'ask about pending decisions, and propose useful next actions. '
        'Respect permissions and report observed outcomes accurately.\n')
    password = secrets.token_urlsafe(24)
    config = {'channel_type': 'web', 'web_host': '127.0.0.1', 'web_port': port,
              'web_password': password, 'agent': True, 'agent_workspace': str(root / 'workspace'),
              'default_agent_id': 'bullgod', 'default_agent_name': 'BullGod',
              'agent_permission_mode': 'read-only', 'self_evolution_enabled': False,
              'knowledge': False, 'subagent': {'enabled': False}, 'external_api_enabled': False}
    if model_base:
        config.update({'model': model, 'bot_type': 'openai', 'open_ai_api_base': model_base,
                       'open_ai_api_key': '', 'open_ai_api_type': 'responses',
                       'debug': False, 'language': 'en'})
    if endpoints:
        config['personal_http_endpoints'] = endpoints
        config['personal_http_relays'] = relays
    fd = os.open(root / 'data/config.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as config_file:
        json.dump(config, config_file, indent=2)
    info = {'version': 1, 'root': str(root), 'port': port, 'python': python}
    if model_base:
        info.update({'model_base': model_base, 'model': model, 'model_key_env': key_env})
        (root / 'model_bootstrap.py').write_text(MODEL_BOOTSTRAP)
    if endpoints:
        shutil.copyfile(REPO / 'scripts/bullgod_https_relay.py', root / 'https_relay.py')
        info['read_relays'] = [{'url': url, 'port': relays[url], 'address': addresses[0]}
                               for url, addresses in endpoints.items()]
    (root / 'instance.json').write_text(json.dumps(info, indent=2))
    # Default-deny filesystem and network; only the instance and runtime are visible.
    read_paths = [root, '/System', '/usr/lib', '/usr/share', '/usr/bin', '/bin', '/sbin',
                  framework, '/private/var/db/dyld', prefix / 'lib', prefix / 'bin', prefix / 'pyvenv.cfg',
                  '/dev/null', '/dev/random', '/dev/urandom', '/dev/dtracehelper']
    profile = '(version 1)\n(deny default)\n(allow process-exec process-fork sysctl-read)\n'
    for path in read_paths:
        profile += f'(allow file-read* (subpath {quoted(path)}))\n'
    for parent in {p for path in (root, prefix) for p in (path, *path.parents)}:
        profile += f'(allow file-read* (literal {quoted(parent)}))\n'
    profile += f'(allow file-write* (subpath {quoted(root)}))\n'
    profile += '(allow file-write* (literal "/dev/null") (literal "/dev/dtracehelper"))\n(deny network*)\n'
    profile += f'(allow network-bind (local ip "localhost:{port}"))\n(allow network-inbound (local ip "localhost:{port}"))\n'
    if model_port:
        profile += f'(allow network-outbound (remote ip "localhost:{model_port}"))\n'
    for relay_port in relays.values():
        profile += f'(allow network-outbound (remote ip "localhost:{relay_port}"))\n'
    (root / 'sandbox.sb').write_text(profile)
    print(root)


def print_ready(root, port):
    print(f'http://127.0.0.1:{port}/\nCredentials: {root / "data/config.json"}\nRoot: {root}')


def _stop_relays(root):
    marker = root / 'relay-processes.json'
    if not marker.exists():
        return
    records = json.loads(marker.read_text())
    for state in records:
        current = identity(state['pid'])
        if current and (current != state['identity'] or str(root / 'https_relay.py') not in current):
            raise RuntimeError('Relay process identity differs; no signal sent')
        if current:
            os.kill(state['pid'], signal.SIGTERM)
    for state in records:
        for _ in range(50):
            if identity(state['pid']) != state['identity']:
                break
            time.sleep(.1)
        else:
            raise RuntimeError('Owned relay did not stop')
    marker.unlink()


def _start_relays(root, info):
    marker = root / 'relay-processes.json'
    if marker.exists():
        _stop_relays(root)
    records = []
    try:
        for relay in info.get('read_relays', []):
            command = [info['python'], str(root / 'https_relay.py'),
                       '--listen-port', str(relay['port']), '--upstream-ip', relay['address']]
            proc = subprocess.Popen(command, env=service_environment(root), cwd=root,
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, start_new_session=True)
            # Python.framework can exec its app launcher during startup. Record
            # identity only after the relay has bound and signalled readiness.
            ready = select.select([proc.stdout], [], [], 5)[0]
            line = proc.stdout.readline() if ready else b''
            proc.stdout.close()
            if line != b'relay ready\n':
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)
                raise RuntimeError('Owned HTTPS relay did not become ready')
            current = identity(proc.pid)
            if not current or str(root / 'https_relay.py') not in current:
                if proc.poll() is None:
                    proc.terminate()
                    proc.wait(timeout=5)
                raise RuntimeError('Owned HTTPS relay failed to start')
            records.append({'pid': proc.pid, 'identity': current})
            marker.write_text(json.dumps(records))
            time.sleep(.15)
            if proc.poll() is not None:
                raise RuntimeError('Owned HTTPS relay exited during startup')
    except Exception:
        _stop_relays(root)
        raise


def start(root, info):
    # Refuse before disturbing relays belonging to an already running instance.
    pidfile = root / 'process.json'
    if pidfile.exists():
        state = json.loads(pidfile.read_text())
        if state['identity'] and identity(state['pid']) == state['identity']:
            raise RuntimeError('Instance is already running')
    _start_relays(root, info)
    try:
        _start_app(root, info)
    except Exception:
        if pidfile.exists():
            stop(root)
        else:
            _stop_relays(root)
        raise


def _start_app(root, info):
    pidfile = root / 'process.json'
    if pidfile.exists():
        state = json.loads(pidfile.read_text())
        if identity(state['pid']) == state['identity'] and state['identity']:
            raise RuntimeError('Instance is already running')
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', info['port']))
    env = service_environment(root)
    entrypoint = root / 'source/app.py'
    if info.get('model_base'):
        model_endpoint(info['model_base'])
        key = os.environ.get(info['model_key_env'], '')
        if not key:
            raise ValueError('Selected model credential environment variable is unavailable')
        env['BULLGOD_DEV_MODEL_KEY'] = key
        entrypoint = root / 'model_bootstrap.py'
    with (root / 'service.log').open('ab') as log:
        proc = subprocess.Popen(['/usr/bin/sandbox-exec', '-f', str(root / 'sandbox.sb'), info['python'], str(entrypoint)],
                                cwd=root / 'source', env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    time.sleep(.2)
    current = identity(proc.pid)
    if proc.poll() is not None or not current or str(entrypoint) not in current:
        raise RuntimeError(f'Service failed to start; see {root / "service.log"}')
    pidfile.write_text(json.dumps({'pid': proc.pid, 'identity': current}))
    for _ in range(100):
        if proc.poll() is not None:
            raise RuntimeError(f'Service exited; see {root / "service.log"}')
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{info["port"]}/api/health', timeout=.5) as response:
                if response.status == 200:
                    print_ready(root, info['port'])
                    return
        except OSError:
            time.sleep(.1)
    raise RuntimeError(f'Service did not become healthy; see {root / "service.log"}; use stop to terminate it')


def stop(root):
    pidfile = root / 'process.json'
    if not pidfile.exists():
        _stop_relays(root)
        return
    state = json.loads(pidfile.read_text())
    if not identity(state['pid']):
        pidfile.unlink()
        _stop_relays(root)
        return
    if (not state['identity'] or identity(state['pid']) != state['identity']
            or not any(str(root / name) in state['identity'] for name in ('source/app.py', 'model_bootstrap.py'))):
        raise RuntimeError('Recorded process is not the owned service; no signal sent')
    os.kill(state['pid'], signal.SIGTERM)
    for _ in range(100):
        if identity(state['pid']) != state['identity']:
            pidfile.unlink()
            _stop_relays(root)
            print('Stopped')
            return
        time.sleep(.1)
    raise RuntimeError('Service did not stop; no further signal sent')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('init', help='create a fresh isolated instance (reset creates another instance)')
    create.add_argument('--port', type=int, default=19892)
    create.add_argument('--python', required=True, help='absolute path to a compatible CowAgent virtual environment interpreter')
    create.add_argument('--model-base', help='explicit loopback model gateway base URL; outbound remains denied otherwise')
    create.add_argument('--model', help='model ID served by the selected gateway')
    create.add_argument('--model-key-env', default='CODEX_POOLER_API_KEY', help='name only; credential is required at start and is never saved')
    create.add_argument('--read-endpoint', action='append', default=[],
                        help='explicit HTTPS endpoint; pin public addresses and permit only their port 443')
    for command in ('start', 'stop'):
        sub.add_parser(command).add_argument('root')
    args = parser.parse_args()
    try:
        if args.command == 'init':
            init(args.port, args.python, args.model_base, args.model, args.model_key_env, args.read_endpoint)
        else:
            root, info = load(args.root)
            (start(root, info) if args.command == 'start' else stop(root))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
