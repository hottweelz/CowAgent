"""Deterministic tests for bounded analysis and independent artifact checks."""
import hashlib
import json
import uuid

import pytest

from agent.external import contract
from agent.external.analysis import (
    AnalysisVerifier,
    build_prompt,
    expected_report,
    normalize_payload,
    output_schema,
)


def dataset():
    return {
        "schema_version": 1,
        "currency": "USD",
        "records": [
            {"id": "paid-1", "amount_cents": 100, "status": "paid"},
            {"id": "refund-1", "amount_cents": -20, "status": "refund"},
            {"id": "pending-1", "amount_cents": 50, "status": "pending"},
            {"id": "void-1", "amount_cents": 5, "status": "void"},
            {"id": "bad-sign", "amount_cents": -1, "status": "paid"},
            {"id": "paid-1", "amount_cents": -30, "status": "refund"},
            {"id": "pending-bad", "amount_cents": -4, "status": "pending"},
            {"id": "bad-sign", "amount_cents": 2, "status": "paid"},
        ],
    }


def make_spec(*, artifact="report.json"):
    return {
        "task_id": str(uuid.uuid4()),
        "task": {"operation": "analyze_records", "artifact": artifact,
                 "content": json.dumps(dataset(), separators=(",", ":"))},
        "verification": {"acceptance": [], "external_state": []},
    }


def test_normalize_and_expected_report_use_signed_cents_and_ordered_exceptions():
    spec = make_spec()
    payload = normalize_payload(spec["task"]["content"])
    result = expected_report(spec)

    assert payload == dataset()
    assert result == {
        "schema_version": 1,
        "task_id": spec["task_id"],
        "dataset_sha256": contract.digest(payload),
        "record_count": 8,
        "accepted_count": 3,
        "totals": {"paid_cents": 100, "refund_cents": -20,
                   "pending_cents": 50, "net_cents": 80},
        "exceptions": [
            {"index": 3, "id": "void-1", "reason": "excluded_status"},
            {"index": 4, "id": "bad-sign", "reason": "invalid_sign"},
            {"index": 5, "id": "paid-1", "reason": "duplicate_id"},
            {"index": 6, "id": "pending-bad", "reason": "invalid_sign"},
            {"index": 7, "id": "bad-sign", "reason": "duplicate_id"},
        ],
    }


@pytest.mark.parametrize(
    "edit",
    [
        lambda value: value.update(schema_version=True),
        lambda value: value["records"][0].update(amount_cents=True),
        lambda value: value["records"][0].update(status=[]),
        lambda value: value["records"][0].update(extra="no"),
    ],
)
def test_normalize_rejects_type_and_shape_mismatches(edit):
    payload = dataset()
    edit(payload)

    with pytest.raises(ValueError):
        normalize_payload(json.dumps(payload))


def test_prompt_and_output_schema_bind_the_bounded_task():
    spec = make_spec()
    prompt = build_prompt(spec)
    schema = output_schema(spec)

    assert spec["task_id"] in prompt
    assert "Frozen records:" in prompt
    assert "shell" not in prompt.casefold()
    assert "internal delegation" in prompt
    assert schema["additionalProperties"] is False
    assert schema["properties"]["task_id"]["const"] == spec["task_id"]
    assert schema["properties"]["totals"]["additionalProperties"] is False


def completed_row(spec, text):
    raw = text.encode("utf-8")
    return {
        "spec": spec,
        "observation": {
            "task_id": spec["task_id"],
            "task_hash": contract.digest(spec),
            "revision": 1,
            "state": "completed",
            "result": {"artifact": spec["task"]["artifact"],
                       "sha256": hashlib.sha256(raw).hexdigest()},
        },
    }


def publish(export_root, spec, text):
    task_dir = export_root / spec["task_id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / spec["task"]["artifact"]).write_text(text, encoding="utf-8")


def test_verifier_confirms_valid_report_and_observed_artifact(tmp_path):
    spec = make_spec()
    artifact_text = json.dumps(expected_report(spec), separators=(",", ":"))
    export_root = tmp_path / "exports"
    publish(export_root, spec, artifact_text)

    report = AnalysisVerifier(export_root).verify(completed_row(spec, artifact_text))

    assert report["acceptance"]["status"] == "passed"
    assert report["external_state"]["status"] == "confirmed"
    assert report["external_state"]["sha256"] == hashlib.sha256(artifact_text.encode()).hexdigest()


def test_verifier_accepts_full_contract_artifact_identifier_length(tmp_path):
    spec = make_spec(artifact='r' * 70 + '.json')
    assert contract.identifier(spec['task']['artifact'])
    text = json.dumps(expected_report(spec))
    export_root = tmp_path / 'exports'
    publish(export_root, spec, text)
    report = AnalysisVerifier(export_root).verify(completed_row(spec, text))
    assert report['acceptance']['status'] == 'passed'


def test_verifier_rejects_wrong_totals_after_completed_runtime(tmp_path):
    spec = make_spec()
    wrong = expected_report(spec)
    wrong["totals"]["paid_cents"] = 999
    wrong_text = json.dumps(wrong, separators=(",", ":"))
    export_root = tmp_path / "exports"
    publish(export_root, spec, wrong_text)

    report = AnalysisVerifier(export_root).verify(completed_row(spec, wrong_text))

    assert report["acceptance"]["status"] == "failed"
    assert report["external_state"]["status"] == "failed"
    assert report["acceptance"]["reason"] == "artifact_does_not_match_frozen_analysis"


@pytest.mark.parametrize(
    "edit",
    [
        lambda value: value.update(schema_version=True),
        lambda value: value["totals"].update(net_cents=True),
        lambda value: value.update(extra="no"),
        lambda value: value.update(task_id=str(uuid.uuid4())),
        lambda value: value.update(dataset_sha256="0" * 64),
    ],
)
def test_verifier_rejects_schema_type_or_binding_mismatch(tmp_path, edit):
    spec = make_spec()
    invalid = expected_report(spec)
    edit(invalid)
    text = json.dumps(invalid, separators=(",", ":"))
    export_root = tmp_path / "exports"
    publish(export_root, spec, text)

    report = AnalysisVerifier(export_root).verify(completed_row(spec, text))

    assert report["acceptance"]["status"] == "failed"
    assert report["external_state"]["status"] == "failed"


def test_verifier_rejects_artifact_hash_mismatch(tmp_path):
    spec = make_spec()
    text = json.dumps(expected_report(spec), separators=(",", ":"))
    export_root = tmp_path / "exports"
    publish(export_root, spec, text)
    row = completed_row(spec, text)
    row["observation"]["result"]["sha256"] = "0" * 64

    report = AnalysisVerifier(export_root).verify(row)

    assert report["acceptance"]["status"] == "failed"
    assert report["acceptance"]["reason"] == "artifact_runtime_hash_mismatch"


def test_verifier_rejects_runtime_artifact_name_mismatch(tmp_path):
    spec = make_spec()
    text = json.dumps(expected_report(spec), separators=(",", ":"))
    export_root = tmp_path / "exports"
    publish(export_root, spec, text)
    row = completed_row(spec, text)
    row["observation"]["result"]["artifact"] = "other.json"

    report = AnalysisVerifier(export_root).verify(row)

    assert report["acceptance"]["status"] == "failed"
    assert report["acceptance"]["reason"] == "runtime_result_binding_invalid"


def test_verifier_rejects_untrusted_artifact_name_without_reading_outside_root(tmp_path):
    spec = make_spec(artifact="../outside.json")
    export_root = tmp_path / "exports"
    export_root.mkdir()
    outside = export_root / "outside.json"
    outside.write_text("must-not-read", encoding="utf-8")
    row = completed_row(spec, "must-not-read")

    report = AnalysisVerifier(export_root).verify(row)

    assert report["acceptance"]["status"] == "failed"
    assert report["acceptance"]["reason"] == "invalid_task_artifact_binding"
    assert outside.read_text(encoding="utf-8") == "must-not-read"


def test_missing_artifact_is_unverified(tmp_path):
    spec = make_spec()
    row = completed_row(spec, json.dumps(expected_report(spec)))

    report = AnalysisVerifier(tmp_path / "exports").verify(row)

    assert report["acceptance"]["status"] == "unverified"
    assert report["external_state"]["status"] == "unverified"


def test_unsupported_caller_criterion_keeps_acceptance_unverified(tmp_path):
    spec = make_spec()
    spec["verification"]["acceptance"] = [
        {"id": "remote-effect", "type": "remote_delivery_confirmation"}
    ]
    text = json.dumps(expected_report(spec), separators=(",", ":"))
    export_root = tmp_path / "exports"
    publish(export_root, spec, text)

    report = AnalysisVerifier(export_root).verify(completed_row(spec, text))

    assert report["acceptance"]["status"] == "unverified"
    assert report["acceptance"]["caller_checks"][0]["reason"] == "unsupported_check"
    assert report["external_state"]["status"] == "confirmed"


def test_failing_supported_caller_criterion_fails_acceptance(tmp_path):
    spec = make_spec()
    spec["verification"]["acceptance"] = [
        {"id": "caller-expectation", "type": "text_equals",
         "path": "report.json", "expected": "different artifact"}
    ]
    text = json.dumps(expected_report(spec), separators=(",", ":"))
    export_root = tmp_path / "exports"
    publish(export_root, spec, text)

    report = AnalysisVerifier(export_root).verify(completed_row(spec, text))

    assert report["acceptance"]["status"] == "failed"
    assert report["acceptance"]["caller_checks"][0]["reason"] == "artifact_mismatch"


def test_failing_supported_external_state_criterion_fails_confirmation(tmp_path):
    spec = make_spec()
    spec["verification"]["external_state"] = [
        {"id": "caller-state", "type": "sha256", "path": "report.json", "expected": "0" * 64}
    ]
    text = json.dumps(expected_report(spec), separators=(",", ":"))
    export_root = tmp_path / "exports"
    publish(export_root, spec, text)

    report = AnalysisVerifier(export_root).verify(completed_row(spec, text))

    assert report["external_state"]["status"] == "failed"
    assert report["external_state"]["caller_checks"][0]["reason"] == "artifact_mismatch"
