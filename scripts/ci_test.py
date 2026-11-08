"""Run pytest with isolated settings and a Python-level fixture network guard.

This guard does not confine child processes or native networking.
"""
import faulthandler
import os
from pathlib import Path
import socket
import sys
import tempfile

REPO = Path(__file__).resolve().parent.parent


def install_network_guard():
    ports = set()
    unix_paths = set()
    original_bind = socket.socket.bind
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def fixture_bind(sock, address):
        result = original_bind(sock, address)
        if sock.family in {socket.AF_INET, socket.AF_INET6} and isinstance(address, tuple):
            port = sock.getsockname()[1]
            if address[0] in {'127.0.0.1', '::1', 'localhost'} and port != 9899:
                ports.add((port, sock.family))
        elif sock.family == socket.AF_UNIX and isinstance(address, (str, bytes)):
            unix_paths.add(address)
        return result

    def allowed(sock, address):
        if sock.family == socket.AF_UNIX and isinstance(address, (str, bytes)):
            return address in unix_paths
        if sock.family in {socket.AF_INET, socket.AF_INET6} and isinstance(address, tuple):
            host, port = address[:2]
            return (port != 9899 and host in {'127.0.0.1', '::1', 'localhost'}
                    and (port, sock.family) in ports)
        return False

    def fixture_connect(sock, address):
        if not allowed(sock, address):
            raise RuntimeError(f'Network access outside owned fixture denied: {address!r}')
        return original_connect(sock, address)

    def fixture_connect_ex(sock, address):
        if not allowed(sock, address):
            raise RuntimeError(f'Network access outside owned fixture denied: {address!r}')
        return original_connect_ex(sock, address)

    socket.socket.bind = fixture_bind
    socket.socket.connect = fixture_connect
    socket.socket.connect_ex = fixture_connect_ex


def prepare_environment(home, data, cache):
    keep = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL', 'TMPDIR') if key in os.environ}
    os.environ.clear()
    os.environ.update(keep)
    os.environ.update(HOME=str(home), USERPROFILE=str(home), COW_DATA_DIR=str(data),
                      TIKTOKEN_CACHE_DIR=str(cache), PYTHONDONTWRITEBYTECODE='1')
    os.environ['PATH'] = str(Path(sys.executable).absolute().parent) + os.pathsep + keep.get('PATH', '')


def main():
    cache = os.environ.get('TIKTOKEN_CACHE_DIR')
    if not cache or not Path(cache).is_absolute() or not Path(cache).is_dir():
        raise SystemExit('TIKTOKEN_CACHE_DIR must name the prepared absolute cache directory')
    with tempfile.TemporaryDirectory(prefix='cow-ci-') as tmp:
        prepare_environment(Path(tmp) / 'home', Path(tmp) / 'data', cache)
        Path(os.environ['HOME']).mkdir()
        Path(os.environ['COW_DATA_DIR']).mkdir()
        os.chdir(REPO)
        sys.path.insert(0, str(REPO))
        install_network_guard()
        faulthandler.dump_traceback_later(300, repeat=True, file=sys.stderr)
        import pytest
        return pytest.main(sys.argv[1:])


if __name__ == '__main__':
    raise SystemExit(main())
