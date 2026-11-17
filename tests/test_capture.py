"""Offline receipt tests; does not connect to SQL Server."""
import copy
from datetime import datetime, timedelta, timezone

import pytest

from migrationproof.capture import (
    FORMAT, CaptureEvidenceError, assess_capture_pair, check_receipt
)
from migrationproof.core import DatabaseSnapshot, TableSnapshot, canonical_digest


def snapshot(amount="150.00", database="SourceLab"):
    return DatabaseSnapshot(
        database=database,
        tables={"dbo.Orders": TableSnapshot(
            columns={"Amount": "decimal(9,12,2) NULL=False"},
            row_count=3, aggregates={"sum:Amount": amount},
        )},
    )


def receipt(snap, start="2026-11-17T12:00:00Z", end="2026-11-17T12:00:02Z"):
    return {
        "format": FORMAT,
        "database": snap.database,
        "snapshot_sha256": canonical_digest(snap),
        "capture_started_at": start,
        "capture_finished_at": end,
        "transaction_consistency": "NOT_TESTED",
        "clock_trust": "NOT_TESTED",
    }


def test_matching_values_still_incomplete_without_transaction_proof():
    a, b = snapshot(), snapshot(database="TargetLab")
    report = assess_capture_pair(a, b, receipt(a), receipt(b))
    assert report["decision"] == "INCOMPLETE"
    assert report["transactional_coherence"] == "NOT_VERIFIED"
    assert "CROSS_DATABASE_TRANSACTION_CONSISTENCY_NOT_VERIFIED" in report["issues"]


def test_real_difference_survives_incomplete_receipts():
    a, b = snapshot(), snapshot("120.00", "TargetLab")
    report = assess_capture_pair(a, b, receipt(a), receipt(b))
    assert report["decision"] == "DIFFERENCES_FOUND"
    assert report["transactional_coherence"] == "NOT_VERIFIED"


def test_disjoint_and_skewed_windows_flagged():
    a, b = snapshot(), snapshot(database="TargetLab")
    report = assess_capture_pair(
        a, b, receipt(a),
        receipt(b, "2026-11-17T12:10:00Z", "2026-11-17T12:10:04Z"),
    )
    assert "CAPTURE_WINDOWS_DO_NOT_OVERLAP" in report["issues"]
    assert "CAPTURE_START_SKEW_EXCEEDS_POLICY" in report["issues"]


@pytest.mark.parametrize("field,value", [
    ("snapshot_sha256", "0" * 64),
    ("database", "other"),
    ("transaction_consistency", "VERIFIED"),
    ("clock_trust", "VERIFIED"),
    ("capture_started_at", "2026-11-17T12:00:00"),
    ("capture_finished_at", "2026-11-17T11:59:59Z"),
    ("capture_finished_at", "2026-11-17T14:00:00Z"),
    ("format", "unsupported"),
])
def test_misleading_or_invalid_receipt_rejected(field, value):
    snap = snapshot()
    bad = receipt(snap)
    bad[field] = value
    with pytest.raises(CaptureEvidenceError):
        check_receipt(bad, snap)


def test_unexpected_receipt_field_fails_closed():
    snap = snapshot()
    bad = receipt(snap)
    bad["trusted_timestamp"] = True
    with pytest.raises(CaptureEvidenceError):
        check_receipt(bad, snap)


def test_original_snapshot_mutation_invalidates_receipt():
    snap = snapshot()
    signed = receipt(snap)
    changed = snap.model_copy(deep=True)
    changed.tables["dbo.Orders"].row_count = 4
    with pytest.raises(CaptureEvidenceError, match="digest"):
        check_receipt(signed, changed)
