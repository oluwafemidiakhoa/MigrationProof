"""Opt-in, read-only integration gate for the checked-in disposable SQL lab.

This must NEVER run from normal CI or against a business/production instance.
Human operator confirms the exact server is a disposable approved lab.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from migrationproof.core import reconcile
from migrationproof.sqlserver import collect_snapshot

APPROVAL = "I_APPROVE_DISPOSABLE_SQLSERVER_LAB_READS"
DATABASES = ("MigrationProofSourceLab", "MigrationProofTargetLab")
EXPECTED_COLUMNS = {"dbo.Orders": ("OrderID", "Amount")}
EXPECTED_SUMS = ("150.00", "1124.00")


def _validated_options(connection: str) -> dict[str, str]:
    """Parse only a small, unambiguous integrated-auth lab ODBC subset.

    We intentionally do not accept arbitrary ODBC syntax, alternate server or
    catalog aliases, credentials, or driver options in this isolated lab gate.
    """
    if not isinstance(connection, str) or len(connection) > 4096 or "\\x00" in connection:
        raise ValueError("Invalid lab connection configuration")
    allowed = {
        "driver", "server", "database", "trusted_connection",
        "encrypt", "trustservercertificate",
    }
    options: dict[str, str] = {}
    for element in connection.split(";"):
        if not element.strip():
            continue
        if "=" not in element:
            raise ValueError("Malformed lab connection option")
        key, value = element.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key not in allowed or key in options or not value:
            raise ValueError("Unsupported or duplicate lab connection option")
        options[key] = value
    if set(options) != allowed:
        raise ValueError("Exact six-option lab connection profile is required")
    if options["driver"].casefold() != "{odbc driver 18 for sql server}":
        raise ValueError("Lab requires ODBC Driver 18")
    if options["trusted_connection"].casefold() != "yes":
        raise ValueError("Lab requires an integrated read-only identity")
    if options["encrypt"].casefold() != "yes":
        raise ValueError("Lab requires encrypted transport")
    if options["trustservercertificate"].casefold() != "no":
        raise ValueError("Lab requires certificate verification")
    if any(any(char in options[name] for char in ("{", "}", chr(13), chr(10))) for name in ("server", "database")):
        raise ValueError("Invalid lab server or database identity")
    return options


def validate_gate_configuration(
    approval: str | None,
    approved_server: str | None,
    source: str | None,
    target: str | None,
) -> None:
    """Reject unsafe or ambiguous targets before creating SQL connections."""
    if approval != APPROVAL:
        raise ValueError("No explicit disposable lab approval")
    if (not isinstance(approved_server, str) or not approved_server
            or approved_server.strip() != approved_server):
        raise ValueError("Invalid approved lab server")
    if not source or not target:
        raise ValueError("Both lab connection strings are required")
    for conn, database in zip((source, target), DATABASES):
        options = _validated_options(conn)
        if options["server"] != approved_server:
            raise ValueError("Connection server does not match approved lab server")
        if options["database"] != database:
            raise ValueError("Lab database identity mismatch")


def run_lab_gate(source_conn: str, target_conn: str, *, approved_server: str,
                 collector=collect_snapshot) -> dict:
    """Execute two bounded, read-only scans on the documented synthetic fixture."""
    validate_gate_configuration(APPROVAL, approved_server, source_conn, target_conn)
    snapshots = [
        collector(conn, expected_database=db,
                  tables_allowlist=("dbo.Orders",),
                  expected_columns=EXPECTED_COLUMNS,
                  max_tables=1, max_rows_per_table=10, timeout=10,
                  sum_columns=("Amount",))
        for conn, db in zip((source_conn, target_conn), DATABASES)
    ]
    for db, snap, expected_sum in zip(DATABASES, snapshots, EXPECTED_SUMS):
        if snap.database != db or set(snap.tables) != {"dbo.Orders"}:
            raise ValueError("Unexpected lab database/table scope")
        table = snap.tables["dbo.Orders"]
        if table.row_count != 3 or set(table.columns) != set(EXPECTED_COLUMNS["dbo.Orders"]):
            raise ValueError("Synthetic fixture no longer matches expected lab scope")
        if str(table.aggregates.get("sum:Amount")) != expected_sum:
            raise ValueError("Synthetic fixture aggregate mismatch")
    compared = reconcile(snapshots[0], snapshots[1])
    if compared["status"] != "DIFFERENCES_FOUND":
        raise ValueError("Expected synthetic migration defect was not detected")
    return {
        "format": "migrationproof.sqlserver-lab-gate.v1",
        "status": "PASS",
        "scope": "Only checked-in synthetic SQL Server fixture; not customer validation",
        "server_approval": "Operator asserted, not independently authenticated",
        "databases": list(DATABASES),
        "tables": ["dbo.Orders"],
        "expected_difference_detected": True,
        "metadata_visibility_independently_verified": False,
        "rls_absence_verified": False,
        "transactional_consistency_verified": False,
        "production_ready": False,
    }


def main() -> int:
    # Without active operator opt-in, the integration gate is explicitly NOT_TESTED.
    if os.getenv("MIGRATIONPROOF_LAB_APPROVAL") != APPROVAL:
        print("NOT_TESTED: explicit disposable SQL Server lab approval absent")
        return 2
    try:
        source = os.getenv("MIGRATIONPROOF_LAB_SOURCE_CONNECTION")
        target = os.getenv("MIGRATIONPROOF_LAB_TARGET_CONNECTION")
        server = os.getenv("MIGRATIONPROOF_APPROVED_LAB_SERVER")
        validate_gate_configuration(os.getenv("MIGRATIONPROOF_LAB_APPROVAL"),
                                    server, source, target)
        report = run_lab_gate(source, target, approved_server=server)
        output = os.getenv("MIGRATIONPROOF_LAB_RECEIPT")
        if not output:
            raise ValueError("Lab receipt destination is required")
        with Path(output).open("x", encoding="utf-8") as handle:
            json.dump(report, handle, sort_keys=True, indent=2)
            handle.write("\n")
        print("PASS: bounded synthetic lab scans detected the expected discrepancy")
        return 0
    except Exception:
        # Do not echo database driver exceptions (may contain connection details).
        print("INCOMPLETE: lab checks did not pass; consult restricted operator diagnostics")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
