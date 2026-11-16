from migrationproof.core import DatabaseSnapshot, canonical_digest, reconcile


def snapshot(row_count=3, column_type="int"):
    return DatabaseSnapshot.model_validate({
        "database": "demo",
        "tables": {"dbo.Orders": {
            "columns": {"id": column_type},
            "row_count": row_count,
            "aggregates": {"total": 12}
        }}
    })


def test_identical_snapshots_pass():
    result = reconcile(snapshot(), snapshot())
    assert result["status"] == "CHECKS_PASSED"
    assert result["findings"] == []
    assert result["source_sha256"] == result["target_sha256"]


def test_row_count_mismatch():
    result = reconcile(snapshot(), snapshot(row_count=2))
    assert "ROW_COUNT_MISMATCH" in [item["code"] for item in result["findings"]]


def test_column_type_mismatch():
    result = reconcile(snapshot(), snapshot(column_type="bigint"))
    assert "COLUMN_TYPE_MISMATCH" in [item["code"] for item in result["findings"]]


def test_digest_is_deterministic():
    assert canonical_digest(snapshot()) == canonical_digest(snapshot())


def test_missing_table():
    target = DatabaseSnapshot(database="demo", tables={})
    assert reconcile(snapshot(), target)["findings"][0]["code"] == "MISSING_TARGET_TABLE"


def test_aggregate_mismatch():
    target = snapshot()
    target.tables["dbo.Orders"].aggregates["total"] = 13
    assert "AGGREGATE_MISMATCH" in [f["code"] for f in reconcile(snapshot(), target)["findings"]]
