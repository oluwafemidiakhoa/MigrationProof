"""Offline transaction lifecycle tests; no SQL Server connectivity."""
import sys
from types import SimpleNamespace

import pytest

from migrationproof.sqlserver import collect_snapshot

CONNECTION = (
    "DRIVER={ODBC Driver 18 for SQL Server};SERVER=LAB-SQL;"
    "DATABASE=MigrationProofSourceLab;Trusted_Connection=yes;"
    "Encrypt=yes;TrustServerCertificate=no;"
)


class FakeCursor:
    def __init__(self, enabled=True, fail_read=False, row_count=1):
        self.enabled = enabled
        self.fail_read = fail_read
        self.row_count = row_count
        self.queries = []
        self.rows = []

    def execute(self, sql):
        self.queries.append(sql)
        if "snapshot_isolation_state FROM sys.databases" in sql:
            self.rows = [(1 if self.enabled else 0,)]
        elif sql == "SELECT DB_NAME()":
            self.rows = [("MigrationProofSourceLab",)]
        elif "FROM sys.tables" in sql:
            self.rows = [("dbo", "Orders", "Amount", "decimal", 9, 12, 2, False)]
        elif "FROM [dbo].[Orders]" in sql:
            if self.fail_read:
                raise RuntimeError("synthetic query failure")
            self.rows = [(self.row_count, "150.00")]
        elif sql in ("SET TRANSACTION ISOLATION LEVEL SNAPSHOT", "BEGIN TRANSACTION",
                     "IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION"):
            self.rows = []
        else:
            raise AssertionError(f"Unexpected query: {sql}")
        return self

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def __iter__(self):
        return iter(self.rows)


class FakeConn:
    def __init__(self, cursor):
        self.cur = cursor
        self.timeout = None

    def cursor(self):
        return self.cur

    def close(self):
        pass


def run(monkeypatch, cursor, snapshot=True):
    conn = FakeConn(cursor)
    monkeypatch.setitem(
        sys.modules, "pyodbc",
        SimpleNamespace(connect=lambda *args, **kwargs: conn),
    )
    return collect_snapshot(
        CONNECTION, expected_database="MigrationProofSourceLab",
        tables_allowlist=("dbo.Orders",),
        expected_columns={"dbo.Orders": ("Amount",)},
        sum_columns=("Amount",), max_rows_per_table=3,
        max_tables=1, snapshot_isolation=snapshot,
    )


def test_snapshot_mode_begins_then_rolls_back(monkeypatch):
    cursor = FakeCursor()
    result = run(monkeypatch, cursor)
    assert result.tables["dbo.Orders"].row_count == 1
    assert cursor.queries[0].startswith("SELECT snapshot_isolation_state")
    assert cursor.queries[1:3] == [
        "SET TRANSACTION ISOLATION LEVEL SNAPSHOT", "BEGIN TRANSACTION"
    ]
    assert cursor.queries[-1] == "IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION"
    assert cursor.queries.index("BEGIN TRANSACTION") < cursor.queries.index("SELECT DB_NAME()")


def test_disabled_snapshot_preflight_refuses_all_table_reads(monkeypatch):
    cursor = FakeCursor(enabled=False)
    with pytest.raises(ValueError, match="not enabled"):
        run(monkeypatch, cursor)
    assert len(cursor.queries) == 1


def test_read_failure_always_rolls_back(monkeypatch):
    cursor = FakeCursor(fail_read=True)
    with pytest.raises(RuntimeError, match="synthetic query failure"):
        run(monkeypatch, cursor)
    assert cursor.queries[-1] == "IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION"


def test_oversized_result_always_rolls_back(monkeypatch):
    cursor = FakeCursor(row_count=4)
    with pytest.raises(ValueError, match="Row budget exceeded"):
        run(monkeypatch, cursor)
    assert cursor.queries[-1] == "IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION"


def test_default_mode_does_not_claim_snapshot_transaction(monkeypatch):
    cursor = FakeCursor()
    result = run(monkeypatch, cursor, snapshot=False)
    assert result.tables["dbo.Orders"].row_count == 1
    assert not any("TRANSACTION" in sql or "snapshot_isolation_state" in sql
                   for sql in cursor.queries)


def test_invalid_mode_fails_before_connection(monkeypatch):
    monkeypatch.setitem(
        sys.modules, "pyodbc",
        SimpleNamespace(connect=lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("must not connect"))),
    )
    with pytest.raises(ValueError, match="boolean"):
        collect_snapshot(
            CONNECTION, expected_database="MigrationProofSourceLab",
            tables_allowlist=("dbo.Orders",), expected_columns={"dbo.Orders": ("Amount",)},
            snapshot_isolation="yes",
        )
