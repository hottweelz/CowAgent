"""Checks for the isolated CI runner and changed-file lint gate."""
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from scripts import ci_test


def test_runner_environment_removes_credentials_and_preserves_cache(monkeypatch, tmp_path):
    monkeypatch.setenv('OPENAI_API_KEY', 'secret')
    monkeypatch.setenv('COW_BROWSER_NATIVE_TEST', '1')
    monkeypatch.setenv('PATH', '/usr/bin')
    monkeypatch.setattr(os, 'environ', os.environ.copy())
    ci_test.prepare_environment(tmp_path / 'home', tmp_path / 'data', tmp_path / 'cache')
    assert 'OPENAI_API_KEY' not in os.environ
    assert 'COW_BROWSER_NATIVE_TEST' not in os.environ
    assert os.environ['TIKTOKEN_CACHE_DIR'] == str(tmp_path / 'cache')
    assert os.environ['HOME'] == str(tmp_path / 'home')
    assert os.environ['COW_DATA_DIR'] == str(tmp_path / 'data')
    assert os.environ['PATH'].split(os.pathsep)[0] == str(Path(sys.executable).absolute().parent)


def test_network_guard_allows_owned_loopback_and_denies_other_endpoints(monkeypatch):
    for name in ('bind', 'connect', 'connect_ex'):
        monkeypatch.setattr(socket.socket, name, getattr(socket.socket, name))
    ci_test.install_network_guard()
    with socket.socket() as server, socket.socket() as client:
        server.bind(('127.0.0.1', 0))
        server.listen()
        client.connect(server.getsockname())
        with pytest.raises(RuntimeError):
            socket.socket().connect(('127.0.0.1', 9899))
        with pytest.raises(RuntimeError):
            socket.socket().connect_ex(('192.0.2.1', 80))


def test_lint_rejects_invalid_base():
    script = Path(ci_test.REPO) / 'scripts' / 'ci_lint.py'
    result = subprocess.run([sys.executable, str(script)], env={**os.environ, 'BASE_SHA': 'bad'},
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert 'BASE_SHA must' in result.stderr


def test_lint_keeps_whitespace_and_omits_deleted_files(monkeypatch, tmp_path):
    from scripts import ci_lint

    monkeypatch.chdir(tmp_path)
    (tmp_path / 'file with spaces.py').write_text('value = 1\n')
    monkeypatch.setenv('BASE_SHA', 'a' * 40)
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, b'file with spaces.py\0deleted.py\0')

    def call(args):
        calls.append(args)
        return 0

    monkeypatch.setattr(ci_lint.subprocess, 'run', run)
    monkeypatch.setattr(ci_lint.subprocess, 'call', call)
    assert ci_lint.main() == 0
    assert calls[-1][-1] == 'file with spaces.py'
    assert 'deleted.py' not in calls[-1]
