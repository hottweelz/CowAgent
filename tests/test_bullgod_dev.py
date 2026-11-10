"""Focused checks for the disposable launcher boundary."""
import contextlib
import io
import importlib.util
import json
from pathlib import Path
import tempfile
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


if __name__ == '__main__':
    unittest.main()
