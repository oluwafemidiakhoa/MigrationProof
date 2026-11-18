"""Negative cases and subprocess check for pilot-readiness evidence gate."""
import json
import subprocess
import sys

from migrationproof.pilot_readiness import evaluate_pre_pilot


def synthetic_receipt():
    return {
        "format": "migrationproof.sqlserver-lab-gate.v1",
        "status": "PASS",
        "production_ready": False,
        "expected_difference_detected": True,
        "databases": ["MigrationProofSourceLab", "MigrationProofTargetLab"],
        "tables": ["dbo.Orders"],
        "metadata_visibility_independently_verified": False,
        "rls_absence_verified": False,
        "transactional_consistency_verified": False,
    }


def test_missing_lab_evidence_is_no_go():
    report = evaluate_pre_pilot()
    assert report["decision"] == "NO_GO"
    assert report["execution_authorized"] is False
    assert report["gates"]["synthetic_lab_execution"] == "NOT_TESTED"


def test_synthetic_lab_receipt_does_not_authorize_pilot():
    report = evaluate_pre_pilot(synthetic_receipt())
    assert report["decision"] == "NO_GO"
    assert report["gates"]["synthetic_lab_execution"] == "REPORTED_SYNTHETIC_PASS_UNAUTHENTICATED"
    assert report["gates"]["verified_tls_certificate_chain"] == "NOT_TESTED"
    assert report["execution_authorized"] is False


def test_misleading_receipt_fails_closed():
    example = synthetic_receipt()
    example["production_ready"] = True
    report = evaluate_pre_pilot(example)
    assert report["gates"]["synthetic_lab_execution"] == "INVALID_EVIDENCE"
    assert report["decision"] == "NO_GO"


def test_cli_writes_no_go_report(tmp_path):
    output = tmp_path / "pilot.json"
    cmd = [sys.executable, "-m", "migrationproof.pilot_readiness_cli", "--output", str(output)]
    completed = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    assert completed.returncode == 2
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["decision"] == "NO_GO"
    assert report["execution_authorized"] is False
    repeated = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    assert repeated.returncode != 0
    assert json.loads(output.read_text(encoding="utf-8")) == report
