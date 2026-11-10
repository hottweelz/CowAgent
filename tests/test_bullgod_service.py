"""Focused tests for persistent BullGod lifecycle safety."""
import json
from pathlib import Path
import plistlib

import pytest

from scripts import bullgod_service as service
from scripts.bullgod_dev import configured_model


def test_root_rejects_temporary_and_relative_paths():
    with pytest.raises(ValueError):
        service.validate_root('relative')
    with pytest.raises(ValueError):
        service.validate_root('/private/tmp/bullgod')


def test_plist_is_manual_and_does_not_contain_secret(tmp_path):
    info = {'python': '/absolute/venv/bin/python'}
    doc = service.plist(tmp_path, info, 'app', ['run-app', str(tmp_path)])
    assert doc['RunAtLoad'] is True
    assert doc['KeepAlive'] is False
    assert doc['StandardErrorPath'] == '/dev/null'
    assert 'EnvironmentVariables' not in doc
    assert 'secret-value' not in plistlib.dumps(doc).decode()
    assert 'LaunchAgents' not in str(tmp_path)


def test_new_instance_default_and_explicit_pin():
    assert configured_model('http://127.0.0.1:4000/api', None) == 'gpt-6-luna'
    assert configured_model('http://127.0.0.1:4000/api', 'gpt-5.6-luna') == 'gpt-5.6-luna'


def test_init_separates_secret_from_instance_and_launchd(tmp_path, monkeypatch):
    root = tmp_path / 'BullGod'
    monkeypatch.setenv('CODEX_POOLER_API_KEY', 'secret-value')
    monkeypatch.setattr(service.sys, 'platform', 'darwin')
    monkeypatch.setattr(service, 'validate_root', lambda path: Path(path))

    def fake_init(port, python, model_base, model, key_env, endpoints, root):
        root.mkdir(mode=0o700)
        (root / 'instance.json').write_text(json.dumps({
            'version': 1, 'root': str(root), 'port': port, 'python': python,
            'read_relays': [{'port': 20000, 'address': '8.8.8.8', 'url': endpoints[0]}],
        }))

    monkeypatch.setattr(service.dev, 'init', fake_init)
    service.init(str(root), 18991, '/absolute/venv/bin/python', 'http://127.0.0.1:4000/api',
                 None, 'CODEX_POOLER_API_KEY', ['https://example.com/news'])
    key = tmp_path / 'BullGod-secrets/model-key'
    assert key.read_text() == 'secret-value'
    assert key.stat().st_mode & 0o077 == 0
    for path in root.rglob('*'):
        if path.is_file():
            assert b'secret-value' not in path.read_bytes()
    for path in (root / 'launchd').glob('*.plist'):
        doc = plistlib.loads(path.read_bytes())
        assert doc['RunAtLoad'] and doc['KeepAlive'] is False


def test_stop_checks_all_identities_before_bootout(tmp_path, monkeypatch):
    calls = []
    def check(root, suffix):
        if suffix == 'relay-0':
            raise RuntimeError('identity mismatch')
        return {'pid': None}
    monkeypatch.setattr(service, 'job_info', check)
    monkeypatch.setattr(service.subprocess, 'run', lambda *args, **kwargs: calls.append(args))
    with pytest.raises(RuntimeError):
        service.stop(tmp_path, {'read_relays': [{}]})
    assert not calls


def test_startup_exit_reports_only_safe_fields(tmp_path, monkeypatch):
    (tmp_path / 'data').mkdir()
    service.phase(tmp_path, 'app', 'app exec')
    monkeypatch.setattr(service, 'job_info', lambda *args: {'state': 'exited', 'pid': None, 'exit': '1'})
    with pytest.raises(service.StartupFailure, match=r'app exited.*phase: app exec; exit: 1'):
        service.ready_or_failed(tmp_path, 'app', 18991, lambda port: False)


def test_stop_waits_for_owned_process_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(service, 'job_info', lambda *args: {'pid': '123'})
    identities = iter(['owned', 'owned', ''])
    monkeypatch.setattr(service.dev, 'identity', lambda pid: next(identities))
    monkeypatch.setattr(service.subprocess, 'run', lambda *args, **kwargs: None)
    monkeypatch.setattr(service.time, 'sleep', lambda seconds: None)
    service.stop(tmp_path, {'read_relays': []})
