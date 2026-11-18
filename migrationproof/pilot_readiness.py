"""Deterministic, fail-closed pre-pilot evidence assessment.

A self-authored or synthetic lab receipt cannot authorize customer work.
This assessor evaluates *available* evidence and always leaves unverified
production-critical gates unresolved. It never connects to a database.
"""
from __future__ import annotations

import json
from typing import Any

FORMAT = "migrationproof.prepilot-assessment.v1"
LAB_FORMAT = "migrationproof.sqlserver-lab-gate.v1"


def evaluate_pre_pilot(lab_receipt: Any = None) -> dict[str, Any]:
    """Report exactly what a supplied synthetic lab receipt establishes.

    Deliberately cannot produce an automatic GO. Real server identity,
    customer authorization and independent reviewer signoff must be checked
    outside the application; arbitrary JSON must not be treated as a grant.
    """
    lab_status = "NOT_TESTED"
    findings: list[str] = []
    if lab_receipt is not None:
        if not isinstance(lab_receipt, dict):
            lab_status = "INVALID_EVIDENCE"
            findings.append("LAB_RECEIPT_NOT_OBJECT")
        elif (
            lab_receipt.get("format") != LAB_FORMAT
            or lab_receipt.get("status") != "PASS"
            or lab_receipt.get("production_ready") is not False
            or lab_receipt.get("expected_difference_detected") is not True
            or lab_receipt.get("databases")
               != ["MigrationProofSourceLab", "MigrationProofTargetLab"]
            or lab_receipt.get("tables") != ["dbo.Orders"]
            or lab_receipt.get("metadata_visibility_independently_verified") is not False
            or lab_receipt.get("rls_absence_verified") is not False
            or lab_receipt.get("transactional_consistency_verified") is not False
        ):
            lab_status = "INVALID_EVIDENCE"
            findings.append("LAB_RECEIPT_MISSING_REQUIRED_SYNTHETIC_SCOPE_OR_CAVEATS")
        else:
            lab_status = "REPORTED_SYNTHETIC_PASS_UNAUTHENTICATED"

    gates = {
        "synthetic_lab_execution": lab_status,
        "lab_server_identity_independently_verified": "NOT_TESTED",
        "verified_tls_certificate_chain": "NOT_TESTED",
        "least_privilege_and_metadata_visibility": "NOT_TESTED",
        "snapshot_concurrency_and_rollback": "NOT_TESTED",
        "cross_database_temporal_coherence": "NOT_TESTED",
        "bounded_query_plan_and_load": "NOT_TESTED",
        "customer_approval_and_data_minimization": "NOT_TESTED",
        "independent_pilot_review": "NOT_TESTED",
    }
    findings += [
        "NO_TRUSTED_LIVE_SQLSERVER_INTEGRATION_EVIDENCE",
        "NO_INDEPENDENT_LAB_IDENTITY_OR_AUTHORIZATION_EVIDENCE",
        "NO_VERIFIED_CROSS_DATABASE_CONSISTENCY",
        "NO_APPROVED_CUSTOMER_DATA_BOUNDARY",
    ]
    return {
        "format": FORMAT,
        "decision": "NO_GO",
        "pilot_scope": "Real customer database migration assessment",
        "execution_authorized": False,
        "gates": gates,
        "blocking_findings": sorted(set(findings)),
        "limitations": (
            "A synthetic fixture receipt is not independent proof of source "
            "authenticity, lab authorization, production security, or whole-database "
            "migration equivalence. Green CI validates only its tested code paths."
        ),
    }


def canonical_report(report: dict[str, Any]) -> str:
    return json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
