"""Run retained regression with external supervision and Codex adapter cases."""
from pathlib import Path
import runpy


if __name__ == '__main__':
    retained = Path(__file__).resolve().parents[1] / 'verification-001/run_regression.py'
    runner = runpy.run_path(str(retained))
    runner['main'](
        extra_files=[
            'tests/test_orchestration_release.py',
            'tests/test_orchestration_persistence_release.py',
            'tests/test_native_tool_contracts_release.py',
            'tests/test_external_contract.py',
            'tests/test_external_runtime.py',
            'tests/test_external_supervisor.py',
            'tests/test_codex_client.py',
            'tests/test_codex_policy.py',
        ],
        evidence_prefix='cowagent-external-002-',
    )
