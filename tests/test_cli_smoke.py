"""Actual subprocess smoke tests for the integrated, offline MigrationProof CLIs.

Synthetic data only. This suite intentionally never connects to SQL Server.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from migrationproof.signatures import SIGNATURE_FORMAT, canonical_manifest_bytes


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def cli(*args):
    return subprocess.run(
        [sys.executable, "-m", *map(str, args)],
        cwd=PROJECT_ROOT,
        capture_output=True, text=True, timeout=20,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT)},
        check=False,
    )


def rows(amounts):
    return {
        "table": "dbo.Orders",
        "key_columns": ["OrderID"],
        "compare_columns": ["Amount"],
        "rows": [{"OrderID": i, "Amount": amount} for i, amount in enumerate(amounts, start=1)],
    }


def prepare(tmp_path, source, target):
    root = tmp_path / "evidence"
    root.mkdir()
    (root / "source_rows.json").write_text(json.dumps(rows(source)), encoding="utf-8")
    (root / "target_rows.json").write_text(json.dumps(rows(target)), encoding="utf-8")
    return root, tmp_path / "manifest.json"


def test_match_bundle_roundtrip_is_incomplete_not_certified(tmp_path):
    root, manifest = prepare(tmp_path, ["10.00", "20.00"], ["10.00", "20.00"])
    made = cli("migrationproof.proof_cli", "create", "--root", root, "--manifest", manifest)
    assert made.returncode == 0, made.stderr + made.stdout
    report = json.loads((root / "comparison.json").read_text(encoding="utf-8"))
    assert report["decision"] == "INCOMPLETE"
    assert report["row_comparison"]["status"] == "SUPPLIED_ROWS_MATCH"
    checked = cli("migrationproof.proof_cli", "verify", "--root", root, "--manifest", manifest)
    assert checked.returncode == 0, checked.stderr + checked.stdout
    assert "authenticity=NOT_TESTED" in checked.stdout
    second = cli("migrationproof.proof_cli", "create", "--root", root, "--manifest", manifest)
    assert second.returncode == 2, "Existing files must not be overwritten"


def test_migration_defect_with_equal_count_and_sum_is_detected(tmp_path):
    root, manifest = prepare(tmp_path, ["10.00", "20.00"], ["20.00", "10.00"])
    made = cli("migrationproof.proof_cli", "create", "--root", root, "--manifest", manifest)
    assert made.returncode == 1, made.stderr + made.stdout
    report = json.loads((root / "comparison.json").read_text(encoding="utf-8"))
    assert report["decision"] == "DIFFERENCES_FOUND"
    assert report["row_comparison"]["changed_matching_keys"] == 2
    checked = cli("migrationproof.proof_cli", "verify", "--root", root, "--manifest", manifest)
    assert checked.returncode == 1, checked.stderr + checked.stdout


def test_modified_input_is_detected_during_verification(tmp_path):
    root, manifest = prepare(tmp_path, ["10.00"], ["10.00"])
    assert cli("migrationproof.proof_cli", "create", "--root", root, "--manifest", manifest).returncode == 0
    (root / "target_rows.json").write_text(json.dumps(rows(["99.00"])), encoding="utf-8")
    result = cli("migrationproof.proof_cli", "verify", "--root", root, "--manifest", manifest)
    assert result.returncode == 2
    assert "INCOMPLETE" in result.stdout


def test_signed_manifest_verified_with_external_key_then_tamper_rejected(tmp_path):
    import base64
    import hashlib

    root, manifest_file = prepare(tmp_path, ["10.00"], ["10.00"])
    assert cli("migrationproof.proof_cli", "create", "--root", root, "--manifest", manifest_file).returncode == 0
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    payload = canonical_manifest_bytes(manifest)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    trusted_path = tmp_path / "trusted_keys.json"
    signature_path = tmp_path / "signature.json"
    trusted_path.write_text(json.dumps({
        "synthetic-test-signer": base64.b64encode(public_key).decode("ascii")
    }), encoding="utf-8")
    signature_path.write_text(json.dumps({
        "format": SIGNATURE_FORMAT,
        "algorithm": "Ed25519",
        "key_id": "synthetic-test-signer",
        "manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "signature_b64": base64.b64encode(private_key.sign(payload)).decode("ascii"),
    }), encoding="utf-8")
    checked = cli(
        "migrationproof.signature_cli",
        "--root", root, "--manifest", manifest_file,
        "--signature", signature_path, "--trusted-keys", trusted_path,
    )
    assert checked.returncode == 0, checked.stderr + checked.stdout
    assert "migration_decision=INCOMPLETE" in checked.stdout

    (root / "comparison.json").write_text('{"decision":"PASS"}', encoding="utf-8")
    tampered = cli(
        "migrationproof.signature_cli",
        "--root", root, "--manifest", manifest_file,
        "--signature", signature_path, "--trusted-keys", trusted_path,
    )
    assert tampered.returncode == 2
    assert "VERIFICATION_FAILED" in tampered.stdout
