import json
from pathlib import Path

import pytest

from migrationproof.proof import (
    ProofError, create_proof, finalize_manifest, verify_proof,
)


def evidence(rows):
    return {
        "table": "dbo.Orders",
        "key_columns": ["OrderID"],
        "compare_columns": ["Amount"],
        "rows": [{"OrderID": i, "Amount": amount} for i, amount in rows],
    }


def write_inputs(root: Path, source, target):
    (root / "source_rows.json").write_text(json.dumps(evidence(source)), encoding="utf-8")
    (root / "target_rows.json").write_text(json.dumps(evidence(target)), encoding="utf-8")


def write_report(root: Path):
    report = create_proof(root)
    (root / "comparison.json").write_text(json.dumps(report), encoding="utf-8")
    return report


def test_matching_rows_remain_incomplete_without_collection_evidence(tmp_path):
    write_inputs(tmp_path, [(1, "10.00")], [(1, "10.00")])
    report = write_report(tmp_path)
    manifest = finalize_manifest(tmp_path)
    verified = verify_proof(tmp_path, manifest)
    assert report == verified
    assert verified["row_comparison"]["status"] == "SUPPLIED_ROWS_MATCH"
    assert verified["decision"] == "INCOMPLETE"
    assert verified["database_completeness"] == "INCOMPLETE"


def test_mismatched_values_are_detected_and_reproducible(tmp_path):
    write_inputs(tmp_path, [(1, "10.00"), (2, "20.00")],
                 [(1, "20.00"), (2, "10.00")])
    report = write_report(tmp_path)
    manifest = finalize_manifest(tmp_path)
    assert report["decision"] == "DIFFERENCES_FOUND"
    assert verify_proof(tmp_path, manifest)["row_comparison"]["changed_matching_keys"] == 2


def test_modified_report_invalidates_proof(tmp_path):
    write_inputs(tmp_path, [(1, "10.00")], [(1, "10.00")])
    write_report(tmp_path)
    manifest = finalize_manifest(tmp_path)
    report_path = tmp_path / "comparison.json"
    report = json.loads(report_path.read_text())
    report["decision"] = "PASS"
    report_path.write_text(json.dumps(report))
    with pytest.raises(ProofError, match="Manifest"):
        verify_proof(tmp_path, manifest)


def test_recomputed_hash_cannot_make_false_report_reproducible(tmp_path):
    write_inputs(tmp_path, [(1, "10.00")], [(1, "10.00")])
    write_report(tmp_path)
    report_path = tmp_path / "comparison.json"
    report = json.loads(report_path.read_text())
    report["decision"] = "PASS"
    report_path.write_text(json.dumps(report))
    revised_manifest = finalize_manifest(tmp_path)
    with pytest.raises(ProofError, match="reproducible"):
        verify_proof(tmp_path, revised_manifest)


def test_missing_input_and_double_creation_fail(tmp_path):
    with pytest.raises(ProofError):
        create_proof(tmp_path)
    write_inputs(tmp_path, [(1, "10.00")], [(1, "10.00")])
    write_report(tmp_path)
    with pytest.raises(ProofError, match="already exists"):
        create_proof(tmp_path)


@pytest.mark.parametrize("bad_manifest", [
    None, {}, {"files": "invalid"}, {"files": [{"path": "source_rows.json"}]},
])
def test_malformed_manifest_rejected(tmp_path, bad_manifest):
    write_inputs(tmp_path, [(1, "10.00")], [(1, "10.00")])
    write_report(tmp_path)
    with pytest.raises(ProofError):
        verify_proof(tmp_path, bad_manifest)


def test_wrong_row_scope_causes_incomplete(tmp_path):
    write_inputs(tmp_path, [(1, "10.00")], [(1, "10.00")])
    source = json.loads((tmp_path / "source_rows.json").read_text())
    source["compare_columns"] = ["Amount", "Missing"]
    (tmp_path / "source_rows.json").write_text(json.dumps(source))
    with pytest.raises(ProofError, match="invalid"):
        create_proof(tmp_path)
