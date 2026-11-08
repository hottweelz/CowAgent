"""Run the retained protected suite with operator and approved-dispatch cases."""
from pathlib import Path
import runpy


if __name__ == '__main__':
    runner = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'verification-001/run_regression.py'))
    runner['main'](extra_files=[
        'tests/test_orchestration_release.py', 'tests/test_orchestration_persistence_release.py',
        'tests/test_native_tool_contracts_release.py', 'tests/test_external_contract.py',
        'tests/test_external_runtime.py', 'tests/test_external_supervisor.py',
        'tests/test_codex_client.py', 'tests/test_codex_policy.py', 'tests/test_codex_adapter.py',
        'tests/test_external_analysis.py', 'tests/test_codex_analysis_policy.py',
        'tests/test_external_operator_review.py', 'tests/test_external_operator_control.py',
        'tests/test_external_operator_cli.py', 'tests/test_approved_dispatch.py',
    ], evidence_prefix='cowagent-external-003b-')
