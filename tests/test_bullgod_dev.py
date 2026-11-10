"""Focused checks for the disposable launcher boundary."""
import contextlib
import io
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('bullgod_dev', Path(__file__).resolve().parents[1] / 'scripts/bullgod_dev.py')
dev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dev)


class DevBoundaryTests(unittest.TestCase):
    def test_rejects_arbitrary_root(self):
        with self.assertRaises(ValueError):
            dev.load(tempfile.gettempdir())

    def test_rejects_private_live_port(self):
        with patch.object(dev.sys, 'platform', 'darwin'), patch.object(Path, 'exists', return_value=True):
            with self.assertRaises(ValueError):
                dev.init(9899, "/unused")

    def test_environment_does_not_inherit_credentials(self):
        with patch.dict(dev.os.environ, {'OPENAI_API_KEY': 'private-canary', 'BROWSER': 'safari'}):
            env = dev.service_environment(Path('/private/test'))
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertEqual(env['BROWSER'], 'true')

    def test_ready_output_contains_only_credential_path(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            dev.print_ready(Path('/private/test'), 19892)
        self.assertIn('/private/test/data/config.json', out.getvalue())
        self.assertNotIn('Password:', out.getvalue())

    def test_rejects_non_absolute_interpreter(self):
        with self.assertRaises(ValueError):
            dev.resolve_python('python')

    def test_rejects_unowned_process_without_signal(self):
        with tempfile.TemporaryDirectory(prefix='bullgod-dev-') as directory:
            root = Path(directory)
            (root / 'process.json').write_text(json.dumps({'pid': 123, 'identity': 'old'}))
            with patch.object(dev, 'identity', return_value='different'), patch.object(dev.os, 'kill') as kill:
                with self.assertRaises(RuntimeError):
                    dev.stop(root)
                kill.assert_not_called()

    def test_model_endpoint_is_explicit_loopback_only(self):
        self.assertEqual(dev.model_endpoint('http://127.0.0.1:4000/backend-api/codex'), 4000)
        for value in ('https://example.com/v1', 'http://127.0.0.1:9899/v1',
                      'http://user:pass@127.0.0.1:4000/v1', 'http://127.0.0.1:4000/v1?key=x'):
            with self.assertRaises(ValueError):
                dev.model_endpoint(value)

    def test_approved_https_endpoint_rejects_private_resolution_and_credentials(self):
        with patch.object(dev.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]):
            self.assertEqual(dev.approved_endpoint('https://news.example/api/news'), ['93.184.216.34'])
            for value in ('http://news.example/api/news', 'https://user:secret@news.example/api/news',
                          'https://news.example/api/news?token=secret', 'https://news.example:8443/api/news'):
                with self.assertRaises(ValueError):
                    dev.approved_endpoint(value)
        with patch.object(dev.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaises(ValueError):
                dev.approved_endpoint('https://news.example/api/news')

    def test_runtime_key_only_enters_selected_gateway_headers(self):
        class Client:
            def _build_headers(self, api_key, extra_headers, url=None):
                return {'Content-Type': 'application/json'}
        module = types.ModuleType('models.openai.openai_http_client')
        module.OpenAIHTTPClient = Client
        with tempfile.TemporaryDirectory(prefix='bullgod-dev-') as directory:
            root = Path(directory)
            (root / 'instance.json').write_text(json.dumps({'model_base': 'http://127.0.0.1:4000/backend-api/codex'}))
            scope = {'__file__': str(root / 'model_bootstrap.py')}
            with patch.dict(dev.os.environ, {'BULLGOD_DEV_MODEL_KEY': 'fictional-fixture-key'}), \
                    patch.dict('sys.modules', {'models.openai.openai_http_client': module}), \
                    patch('runpy.run_path') as app, patch('sys.path', []):
                exec(dev.MODEL_BOOTSTRAP, scope)
                self.assertNotIn('BULLGOD_DEV_MODEL_KEY', dev.os.environ)
                selected = Client()._build_headers(None, None, 'http://127.0.0.1:4000/backend-api/codex/responses')
                self.assertEqual(selected['Authorization'], 'Bearer fictional-fixture-key')
                other = Client()._build_headers(None, None, 'http://127.0.0.1:4001/backend-api/codex/responses')
                self.assertNotIn('Authorization', other)
                app.assert_called_once()
            self.assertNotIn('fictional-fixture-key', (root / 'instance.json').read_text())


if __name__ == '__main__':
    unittest.main()
