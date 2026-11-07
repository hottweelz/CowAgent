"""Preservation boundaries for the opt-in audit runner; no provider calls."""
import pytest

from scripts.benchmark_context_cache import safe_usage, validate_snapshot


def test_snapshot_guard_rejects_active_paths_and_linked_runtime_data(tmp_path):
    active = tmp_path / 'active'
    active.mkdir()
    snapshot = tmp_path / 'snapshot'
    snapshot.mkdir()
    assert validate_snapshot(snapshot, active) == snapshot
    for forbidden in [active, active / 'nested', tmp_path]:
        with pytest.raises(ValueError, match='separate'):
            validate_snapshot(forbidden, active)
    (snapshot / 'index.db').symlink_to(active / 'index.db')
    with pytest.raises(ValueError, match='symlinks'):
        validate_snapshot(snapshot, active)


def test_saved_usage_omits_echoed_strings_and_keeps_nested_cache_counts():
    assert safe_usage({
        'prompt_tokens': 12,
        'prompt_tokens_details': {'cached_tokens': 8, 'echo': 'private text'},
        'untrusted_response': 'secret',
        'untrusted_list': ['private text'],
        'cost': 0,
    }) == {
        'prompt_tokens': 12,
        'prompt_tokens_details': {'cached_tokens': 8},
        'cost': 0,
    }
