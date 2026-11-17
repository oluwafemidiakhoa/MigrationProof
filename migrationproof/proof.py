"""Offline, scoped migration proof report over pre-existing sanitized row evidence.

A proof bundle is a *reproducible comparison report*, not an authenticated
migration certificate. Unknown database collection completeness remains INCOMPLETE.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .evidence import EvidenceError, build_manifest, verify_manifest
from .rows import RowEvidenceError, reconcile_rows

FORMAT = "migrationproof.scoped-proof.v1"
COVERAGE = "INCOMPLETE"
EXPECTED_FILES = ("comparison.json", "source_rows.json", "target_rows.json")


class ProofError(ValueError):
    """Evidence missing, mismatched, or the proof format is invalid."""


def _load_json(root: Path, name: str) -> Any:
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise ProofError("Expected evidence file missing or unsafe")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProofError("Cannot parse expected evidence") from exc


def _computed_report(root: Path) -> dict[str, Any]:
    try:
        compared = reconcile_rows(
            _load_json(root, "source_rows.json"),
            _load_json(root, "target_rows.json"),
        )
    except RowEvidenceError as exc:
        raise ProofError("Row evidence is invalid or ambiguous") from exc
    return {
        "format": FORMAT,
        "database_completeness": COVERAGE,
        "collection_consistency": "NOT_TESTED",
        "source_authenticity": "NOT_TESTED",
        "row_comparison": compared,
        "decision": ("DIFFERENCES_FOUND" if compared["status"] == "DIFFERENCES_FOUND"
                     else "INCOMPLETE"),
        "limitations": (
            "The comparison covers only supplied, sanitized keyed rows. "
            "No collection completeness, SQL transaction consistency, "
            "authenticity, independent validation, or full migration equivalence is established."
        ),
    }


def create_proof(root: Path) -> dict[str, Any]:
    """Create only the report content and manifest in memory; no filesystem writes."""
    root = Path(root).resolve(strict=True)
    report = _computed_report(root)
    if (root / "comparison.json").exists():
        raise ProofError("Comparison report already exists; refuse overwrite")
    # Caller writes the computed comparison with exclusive creation, then
    # computes a manifest using the exact completed bytes.
    return report


def finalize_manifest(root: Path) -> dict[str, Any]:
    """Build manifest for three required evidence files after report is written."""
    try:
        return build_manifest(root, list(EXPECTED_FILES))
    except (EvidenceError, OSError) as exc:
        raise ProofError("Evidence manifest cannot be constructed") from exc


def verify_proof(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    """Rehash all files and reproduce report. Returns report or raises ProofError."""
    root = Path(root).resolve(strict=True)
    if (not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list)
            or any(not isinstance(entry, dict) for entry in manifest["files"])
            or [entry.get("path") for entry in manifest["files"]] != list(EXPECTED_FILES)):
        raise ProofError("Manifest must cover exactly all required evidence")
    try:
        verify_manifest(root, manifest)
    except (EvidenceError, OSError) as exc:
        raise ProofError("Manifest verification failed") from exc
    actual = _load_json(root, "comparison.json")
    expected = _computed_report(root)
    if type(actual) is not dict or actual != expected:
        raise ProofError("Report is not reproducible from supplied rows")
    return expected
