"""Unit tests for the opt-in lab gate. Never connects to a real SQL Server."""
import pytest

from migrationproof.core import DatabaseSnapshot, TableSnapshot
from scripts.run_sqlserver_lab_gate import (
    APPROVAL, EXPECTED_COLUMNS, validate_gate_configuration, run_lab_gate
)


def connection(database, server="LAB-SQL"):
    return (f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};"
            f"DATABASE={database};Trusted_Connection=yes;"
            "Encrypt=yes;TrustServerCertificate=no;")


def test_no_authorization_fails_before_any_connection():
    with pytest.raises(ValueError, match="approval"):
        validate_gate_configuration(
            None, "LAB-SQL", connection("MigrationProofSourceLab"),
            connection("MigrationProofTargetLab")
        )


@pytest.mark.parametrize("source,target,server", [
    (connection("MigrationProofSourceLab", "PROD-SQL"),
     connection("MigrationProofTargetLab"), "LAB-SQL"),
    (connection("MigrationProofSourceLab"),
     connection("MigrationProofTargetLab", "PROD-SQL"), "LAB-SQL"),
    (connection("MigrationProofTargetLab"),
     connection("MigrationProofTargetLab"), "LAB-SQL"),
    (connection("MigrationProofSourceLab") + "SERVER=OTHER;",
     connection("MigrationProofTargetLab"), "LAB-SQL"),
    (connection("MigrationProofSourceLab") + "Initial Catalog=master;",
     connection("MigrationProofTargetLab"), "LAB-SQL"),
    (connection("MigrationProofSourceLab") + "UID=sa;",
     connection("MigrationProofTargetLab"), "LAB-SQL"),
])
def test_unapproved_target_or_ambiguous_options_rejected(source, target, server):
    with pytest.raises(ValueError):
        validate_gate_configuration(APPROVAL, server, source, target)


def test_expected_difference_detected_from_synthetic_snapshots():
    calls = []
    def synthetic_collector(conn, **kwargs):
        calls.append(kwargs)
        db = kwargs["expected_database"]
        total = "150.00" if db == "MigrationProofSourceLab" else "1124.00"
        return DatabaseSnapshot(
            database=db,
            tables={"dbo.Orders": TableSnapshot(
                columns={"OrderID": "int(4,10,0) NULL=False",
                         "Amount": "decimal(9,12,2) NULL=False"},
                row_count=3,
                aggregates={"sum:Amount": total}
            )}
        )
    report = run_lab_gate(
        connection("MigrationProofSourceLab"),
        connection("MigrationProofTargetLab"),
        approved_server="LAB-SQL", collector=synthetic_collector,
    )
    assert report["status"] == "PASS"
    assert report["production_ready"] is False
    assert report["transactional_consistency_verified"] is False
    assert len(calls) == 2
    assert all(c["max_rows_per_table"] == 10 for c in calls)
    assert all(c["timeout"] == 10 for c in calls)
    assert all(c["expected_columns"] == EXPECTED_COLUMNS for c in calls)


def test_unexpected_fixture_aborts():
    def bad_collector(conn, **kwargs):
        return DatabaseSnapshot(
            database=kwargs["expected_database"],
            tables={"dbo.Orders": TableSnapshot(
                columns={"OrderID": "int(4,10,0) NULL=False",
                         "Amount": "decimal(9,12,2) NULL=False"},
                row_count=3, aggregates={"sum:Amount": "150.00"}
            )}
        )
    with pytest.raises(ValueError, match="aggregate"):
        run_lab_gate(connection("MigrationProofSourceLab"),
                     connection("MigrationProofTargetLab"),
                     approved_server="LAB-SQL", collector=bad_collector)
