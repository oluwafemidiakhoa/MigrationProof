"""Offline capture-coherence assessment; never asserts transaction consistency.

Binds operator-supplied observation receipts to the exact snapshot contents.
Timestamp overlap is necessary for some assessments, but never sufficient to
prove a shared transactional state across different SQL Server databases.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .core import DatabaseSnapshot, canonical_digest, reconcile

FORMAT = "migrationproof.capture-receipt.v1"
MAX_CAPTURE_SECONDS = 3600
MAX_CLOCK_SKEW_SECONDS = 300


class CaptureEvidenceError(ValueError):
    """Malformed or contradictory capture receipt."""


def _parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or len(value) > 40:
        raise CaptureEvidenceError("Capture timestamp must be a bounded ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureEvidenceError("Invalid capture timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CaptureEvidenceError("Timezone-aware capture timestamp required")
    return parsed.astimezone(timezone.utc)


def check_receipt(receipt: Any, snapshot: DatabaseSnapshot) -> dict[str, Any]:
    """Validate exact fields, snapshot identity, SHA-256 and time ordering."""
    required = {
        "format", "database", "snapshot_sha256",
        "capture_started_at", "capture_finished_at",
        "transaction_consistency", "clock_trust",
    }
    if not isinstance(receipt, dict) or set(receipt) != required:
        raise CaptureEvidenceError("Receipt has missing or unexpected fields")
    if receipt["format"] != FORMAT:
        raise CaptureEvidenceError("Unsupported receipt format")
    if receipt["database"] != snapshot.database:
        raise CaptureEvidenceError("Receipt database does not match snapshot")
    if receipt["snapshot_sha256"] != canonical_digest(snapshot):
        raise CaptureEvidenceError("Receipt digest does not match snapshot")
    # The current collector does not establish these assurances. Do not accept
    # unsubstantiated PASS / VERIFIED / SNAPSHOT claims from self-reported data.
    if receipt["transaction_consistency"] not in ("NOT_TESTED", "OPERATOR_ASSERTED"):
        raise CaptureEvidenceError("Unsupported transaction consistency claim")
    if receipt["clock_trust"] not in ("NOT_TESTED", "OPERATOR_ASSERTED"):
        raise CaptureEvidenceError("Unsupported clock trust claim")
    start = _parse_utc(receipt["capture_started_at"])
    end = _parse_utc(receipt["capture_finished_at"])
    seconds = (end - start).total_seconds()
    if seconds < 0 or seconds > MAX_CAPTURE_SECONDS:
        raise CaptureEvidenceError("Capture interval is reversed or exceeds allowed duration")
    return {
        "start": start, "end": end,
        "transaction_consistency": receipt["transaction_consistency"],
        "clock_trust": receipt["clock_trust"],
    }


def assess_capture_pair(
    source: DatabaseSnapshot, target: DatabaseSnapshot,
    source_receipt: Any, target_receipt: Any,
) -> dict[str, Any]:
    """Compute discrepancy findings, but never promote metadata into proof."""
    observed_source = check_receipt(source_receipt, source)
    observed_target = check_receipt(target_receipt, target)
    comparison = reconcile(source, target)
    overlap = (
        min(observed_source["end"], observed_target["end"])
        - max(observed_source["start"], observed_target["start"])
    ).total_seconds()
    start_skew = abs(
        (observed_source["start"] - observed_target["start"]).total_seconds()
    )
    issues = []
    if overlap < 0:
        issues.append("CAPTURE_WINDOWS_DO_NOT_OVERLAP")
    if start_skew > MAX_CLOCK_SKEW_SECONDS:
        issues.append("CAPTURE_START_SKEW_EXCEEDS_POLICY")
    issues.append("CROSS_DATABASE_TRANSACTION_CONSISTENCY_NOT_VERIFIED")
    issues.append("CAPTURE_CLOCK_AUTHENTICITY_NOT_VERIFIED")
    return {
        "format": "migrationproof.capture-assessment.v1",
        "decision": (
            "DIFFERENCES_FOUND"
            if comparison["status"] == "DIFFERENCES_FOUND" else "INCOMPLETE"
        ),
        "snapshot_comparison_status": comparison["status"],
        "receipt_binding": "DIGEST_MATCHED_UNAUTHENTICATED",
        "source_window_utc": [
            observed_source["start"].isoformat(),
            observed_source["end"].isoformat(),
        ],
        "target_window_utc": [
            observed_target["start"].isoformat(),
            observed_target["end"].isoformat(),
        ],
        "start_skew_seconds": start_skew,
        "capture_window_overlap_seconds": max(overlap, 0),
        "transactional_coherence": "NOT_VERIFIED",
        "issues": sorted(issues),
        "scope": (
            "Operator-supplied timestamps and digest-bound snapshots only. "
            "Matching results and overlapping windows cannot prove a shared "
            "SQL Server transaction, absence of concurrent mutations or trusted clocks."
        ),
    }
