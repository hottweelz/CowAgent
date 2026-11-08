"""Bounded fictional-record analysis and independent artifact verification."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from agent.external import contract
from agent.external.verification import ExternalVerifier
from agent.permission.authority import Authority
from agent.permission.filesystem import FileBroker, FileDenied


_PAYLOAD_KEYS = {"schema_version", "currency", "records"}
_RECORD_KEYS = {"id", "amount_cents", "status"}
_STATUSES = {"paid", "refund", "pending", "void"}
_REASONS = {"duplicate_id", "excluded_status", "invalid_sign"}
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_PAYLOAD_BYTES = 65536


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = item
    return value


def _reject_constant(value):
    raise ValueError(f"Invalid JSON number: {value}")


def normalize_payload(content):
    """Parse and strictly validate the frozen JSON dataset."""
    if not isinstance(content, str) or len(content.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        raise ValueError("Dataset must be bounded UTF-8 JSON")
    try:
        payload = json.loads(content, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise ValueError("Dataset is not valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != _PAYLOAD_KEYS:
        raise ValueError("Dataset fields do not match the fixed schema")
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("Unsupported dataset schema version")
    if payload["currency"] != "USD":
        raise ValueError("Dataset currency must be USD")
    records = payload["records"]
    if not isinstance(records, list) or not 1 <= len(records) <= 100:
        raise ValueError("Dataset must contain 1 to 100 records")
    for record in records:
        if not isinstance(record, dict) or set(record) != _RECORD_KEYS:
            raise ValueError("Record fields do not match the fixed schema")
        if not isinstance(record["id"], str) or not _IDENTIFIER.fullmatch(record["id"]):
            raise ValueError("Record id is not identifier-like")
        amount = record["amount_cents"]
        if type(amount) is not int or abs(amount) > 1_000_000_000:
            raise ValueError("Record amount must be an integer in range")
        if not isinstance(record["status"], str) or record["status"] not in _STATUSES:
            raise ValueError("Unsupported record status")
    return payload


def _analysis(payload):
    totals = {"paid_cents": 0, "refund_cents": 0, "pending_cents": 0}
    exceptions = []
    seen = set()
    accepted_count = 0
    for index, record in enumerate(payload["records"]):
        record_id = record["id"]
        amount = record["amount_cents"]
        status = record["status"]
        if record_id in seen:
            exceptions.append({"index": index, "id": record_id, "reason": "duplicate_id"})
            continue
        seen.add(record_id)
        if status == "void":
            exceptions.append({"index": index, "id": record_id, "reason": "excluded_status"})
            continue
        if (status in ("paid", "pending") and amount < 0) or (status == "refund" and amount > 0):
            exceptions.append({"index": index, "id": record_id, "reason": "invalid_sign"})
            continue
        totals[f"{status}_cents"] += amount
        accepted_count += 1
    totals["net_cents"] = totals["paid_cents"] + totals["refund_cents"]
    return accepted_count, totals, exceptions


def expected_report(spec):
    """Compute the exact expected JSON report from immutable task input."""
    if not isinstance(spec, dict) or not isinstance(spec.get("task"), dict):
        raise ValueError("Invalid analysis task")
    payload = normalize_payload(spec["task"].get("content"))
    task_id = spec.get("task_id")
    if not contract.task_id(task_id):
        raise ValueError("Invalid analysis task id")
    accepted_count, totals, exceptions = _analysis(payload)
    return {
        "schema_version": 1,
        "task_id": task_id,
        "dataset_sha256": contract.digest(payload),
        "record_count": len(payload["records"]),
        "accepted_count": accepted_count,
        "totals": totals,
        "exceptions": exceptions,
    }


def output_schema(spec):
    """Return the strict JSON output schema for one frozen task."""
    expected = expected_report(spec)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "task_id", "dataset_sha256", "record_count",
                     "accepted_count", "totals", "exceptions"],
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "task_id": {"type": "string", "const": expected["task_id"]},
            "dataset_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "record_count": {"type": "integer", "minimum": 1, "maximum": 100},
            "accepted_count": {"type": "integer", "minimum": 0, "maximum": 100},
            "totals": {
                "type": "object",
                "additionalProperties": False,
                "required": ["paid_cents", "refund_cents", "pending_cents", "net_cents"],
                "properties": {key: {"type": "integer", "minimum": -100_000_000_000,
                                     "maximum": 100_000_000_000} for key in
                               ("paid_cents", "refund_cents", "pending_cents", "net_cents")},
            },
            "exceptions": {
                "type": "array",
                "maxItems": 100,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["index", "id", "reason"],
                    "properties": {
                        "index": {"type": "integer", "minimum": 0, "maximum": 99},
                        "id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$"},
                        "reason": {"type": "string", "enum": sorted(_REASONS)},
                    },
                },
            },
        },
    }


def build_prompt(spec):
    """Build a bounded objective with only the frozen fictional records."""
    expected = expected_report(spec)
    payload = normalize_payload(spec["task"]["content"])
    return (
        "Analyze the fictional USD records below and return one JSON object that "
        "matches the supplied output schema. Do not add prose.\n\n"
        f"Task id: {expected['task_id']}\n"
        f"Dataset SHA-256: {expected['dataset_sha256']}\n\n"
        "Rules:\n"
        "- Process records in input order.\n"
        "- The first occurrence of an id is eligible for analysis. Each later "
        "occurrence is an exception with reason duplicate_id, even when the "
        "first occurrence was excluded.\n"
        "- A unique void record is an exception with reason excluded_status.\n"
        "- A negative paid or pending amount, or positive refund amount, is an "
        "exception with reason invalid_sign. Zero is valid.\n"
        "- Sum valid paid, refund and pending amounts into their signed cent "
        "totals. Net is paid_cents plus refund_cents.\n"
        "- accepted_count counts valid paid, refund and pending records only.\n"
        "- Exception indices are zero-based.\n"
        "- You may use native internal delegation if available; all work remains "
        "within the authority of this task.\n\n"
        "Frozen records:\n"
        + json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    )


def _strict_json(text):
    return json.loads(text, object_pairs_hook=_unique_object, parse_constant=_reject_constant)


def _valid_report_shape(value, task_id):
    keys = {"schema_version", "task_id", "dataset_sha256", "record_count",
            "accepted_count", "totals", "exceptions"}
    if not isinstance(value, dict) or set(value) != keys:
        return False
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1
            or value["task_id"] != task_id or not isinstance(value["task_id"], str)
            or not isinstance(value["dataset_sha256"], str)
            or not _SHA256.fullmatch(value["dataset_sha256"])
            or type(value["record_count"]) is not int or not 1 <= value["record_count"] <= 100
            or type(value["accepted_count"]) is not int or not 0 <= value["accepted_count"] <= 100):
        return False
    totals = value["totals"]
    total_keys = {"paid_cents", "refund_cents", "pending_cents", "net_cents"}
    if (not isinstance(totals, dict) or set(totals) != total_keys
            or any(type(amount) is not int for amount in totals.values())):
        return False
    exceptions = value["exceptions"]
    if not isinstance(exceptions, list):
        return False
    for exception in exceptions:
        if (not isinstance(exception, dict) or set(exception) != {"index", "id", "reason"}
                or type(exception["index"]) is not int or not 0 <= exception["index"] < 100
                or not isinstance(exception["id"], str) or not _IDENTIFIER.fullmatch(exception["id"])
                or not isinstance(exception["reason"], str) or exception["reason"] not in _REASONS):
            return False
    return True


class AnalysisVerifier:
    """Verify a completed runtime artifact through a read-only FileBroker."""

    def __init__(self, export_root):
        self.export_root = Path(export_root).resolve()

    def verify(self, row):
        report = self._verify_fixed_artifact(row)
        spec = row.get("spec", {}) if isinstance(row, dict) else {}
        verification = spec.get("verification", {}) if isinstance(spec, dict) else {}
        configured = {group: verification.get(group, []) for group in ("acceptance", "external_state")}
        if not any(configured.values()):
            return report
        try:
            caller_report = ExternalVerifier(self.export_root).verify(row)
        except Exception:
            caller_report = {
                group: {"status": "unverified", "reason": "caller_verifier_unavailable", "checks": []}
                for group in configured
            }
        for group, checks in configured.items():
            if not checks:
                continue
            caller = caller_report.get(group, {})
            fixed_entry = report[group]
            fixed_status = fixed_entry.get("status", "unverified")
            caller_status = caller.get("status", "unverified")
            normalized_statuses = {self._status_for_merge(group, fixed_status),
                                   self._status_for_merge(group, caller_status)}
            status = ("failed" if "failed" in normalized_statuses else
                      "unverified" if "unverified" in normalized_statuses else "passed")
            fixed_entry["status"] = "confirmed" if group == "external_state" and status == "passed" else status
            fixed_entry["caller_checks"] = caller.get("checks", [])
            fixed_entry["caller_reason"] = caller.get("reason", "caller_checks_" + caller_status)
        return report

    @staticmethod
    def _status_for_merge(group, status):
        if status in ("passed", "confirmed"):
            return "passed"
        if status == "failed":
            return "failed"
        return "unverified"

    def _verify_fixed_artifact(self, row):
        checked_at = datetime.now(timezone.utc).isoformat()
        report = {"verifier": "analysis-artifact-v1", "checked_at": checked_at}
        try:
            spec = row["spec"]
            task_id = spec["task_id"]
            task = spec["task"]
            artifact = task["artifact"]
            expected = expected_report(spec)
            observation = row.get("observation")
            result = observation.get("result") if isinstance(observation, dict) else None
        except (KeyError, TypeError, ValueError):
            return self._unverified(report, "task_or_observation_unavailable")
        if not contract.task_id(task_id) or not contract.identifier(artifact):
            return self._failed(report, "invalid_task_artifact_binding")
        if not isinstance(observation, dict) or observation.get("state") != "completed":
            return self._unverified(report, "execution_not_completed")
        if (observation.get("task_id") != task_id
                or observation.get("task_hash") != contract.digest(spec)):
            return self._failed(report, "execution_task_binding_mismatch")
        if (not isinstance(result, dict) or result.get("artifact") != artifact
                or not isinstance(result.get("sha256"), str)
                or not _SHA256.fullmatch(result["sha256"])):
            return self._failed(report, "runtime_result_binding_invalid")

        root = self.export_root / task_id
        authority = Authority("read-only", frozenset({"fs.read"}), (str(root),), ())
        broker = FileBroker(authority, str(root))
        try:
            raw = broker.read(artifact).encode("utf-8")
        except FileDenied:
            return self._unverified(report, "artifact_access_unavailable")
        except (OSError, UnicodeError):
            return self._unverified(report, "artifact_access_unavailable")
        observed_sha256 = hashlib.sha256(raw).hexdigest()
        if observed_sha256 != result["sha256"]:
            return self._failed(report, "artifact_runtime_hash_mismatch", observed_sha256)
        try:
            actual = _strict_json(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeError, ValueError, RecursionError):
            return self._failed(report, "artifact_invalid_json", observed_sha256)
        if not _valid_report_shape(actual, task_id):
            return self._failed(report, "artifact_schema_invalid", observed_sha256)
        if actual != expected:
            return self._failed(report, "artifact_does_not_match_frozen_analysis", observed_sha256)
        report["acceptance"] = {"status": "passed", "reason": "artifact_matches_frozen_analysis",
                                "artifact": artifact, "sha256": observed_sha256,
                                "record_count": expected["record_count"],
                                "accepted_count": expected["accepted_count"]}
        report["external_state"] = {"status": "confirmed", "reason": "artifact_read_and_hash_confirmed",
                                    "artifact": artifact, "sha256": observed_sha256}
        return report

    @staticmethod
    def _failed(report, reason, sha256=None):
        report["acceptance"] = {"status": "failed", "reason": reason}
        report["external_state"] = {"status": "failed", "reason": reason}
        if sha256 is not None:
            report["external_state"]["observed_sha256"] = sha256
        return report

    @staticmethod
    def _unverified(report, reason):
        report["acceptance"] = {"status": "unverified", "reason": reason}
        report["external_state"] = {"status": "unverified", "reason": reason}
        return report
