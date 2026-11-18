"""No-network tests of SQL runtime identity and encryption preflight."""
import sys
from types import SimpleNamespace

import pytest

from migrationproof.sqlserver import collect_snapshot

CONNECTION = (
    "DRIVER={ODBC Driver 18 for SQL Server};SERVER=LAB-SQL;"
    "DATABASE=MigrationProofSourceLab;Trusted_Connection=yes;"
    "Encrypt=yes;TrustServerCertificate=no;"
)


class Cursor:
    def __init__(self, instance="LAB-SQL", encrypted="TRUE"):
        self.instance = instance
        self.encrypted = encrypted
        self.sql = []
        self.rows = []

    def execute(self, sql):
        self.sql.append(sql)
        if "SERVERPROPERTY('ServerName')" in sql:
            self.rows = [(self.instance,)]
        elif "FROM sys.dm_exec_connections" in sql:
            self.rows = [(self.encrypted,)]
        elif sql == "SELECT DB_NAME()":
            self.rows = [("MigrationProofSourceLab",)]
        elif "FROM sys.tables" in sql:
            self.rows = [("dbo", "Orders", "Amount", "decimal", 9, 12, 2, False)]
        elif "FROM [dbo].[Orders]" in sql:
            self.rows = [(1, "50.00")]
        else:
            raise AssertionError("Unexpected SQL command")
        return self

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def __iter__(self):
        return iter(self.rows)


class Conn:
    def __init__(self, cursor):
        self.cur = cursor
        self.timeout = None

    def cursor(self):
        return self.cur

    def close(self):
        pass


def run(monkeypatch, instance="LAB-SQL", encrypted="TRUE", **options):
    cursor = Cursor(instance, encrypted)
    monkeypatch.setitem(sys.modules, "pyodbc", SimpleNamespace(
        connect=lambda *args, **kwargs: Conn(cursor),
    ))
    try:
        result = collect_snapshot(
            CONNECTION, expected_database="MigrationProofSourceLab",
            tables_allowlist=("dbo.Orders",), expected_columns={"dbo.Orders": ("Amount",)},
            sum_columns=("Amount",), max_tables=1, max_rows_per_table=3, **options,
        )
        return result, cursor.sql
    finally:
        run.last_sql = cursor.sql


def test_expected_instance_and_runtime_encryption_success(monkeypatch):
    result, sql = run(monkeypatch, expected_instance="LAB-SQL",
                      require_encrypted_session=True)
    assert result.tables["dbo.Orders"].row_count == 1
    assert "SERVERPROPERTY('ServerName')" in sql[0]
    assert "sys.dm_exec_connections" in sql[1]


def test_wrong_instance_aborts_before_table_read(monkeypatch):
    with pytest.raises(ValueError, match="instance identity mismatch"):
        run(monkeypatch, instance="PROD-SQL", expected_instance="LAB-SQL",
            require_encrypted_session=True)
    assert len(run.last_sql) == 1


@pytest.mark.parametrize("observed", ["FALSE", None, "UNKNOWN"])
def test_unencrypted_or_unknown_session_aborts(monkeypatch, observed):
    with pytest.raises(ValueError, match="session encryption"):
        run(monkeypatch, encrypted=observed, expected_instance="LAB-SQL",
            require_encrypted_session=True)
    assert len(run.last_sql) == 2


def test_default_mode_unchanged(monkeypatch):
    result, sql = run(monkeypatch)
    assert result.tables["dbo.Orders"].row_count == 1
    assert not any("SERVERPROPERTY" in query or "dm_exec_connections" in query for query in sql)


def test_invalid_preflight_flags_fail_before_connect(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyodbc", SimpleNamespace(
        connect=lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not connect")),
    ))
    with pytest.raises(ValueError, match="boolean"):
        collect_snapshot(
            CONNECTION, expected_database="MigrationProofSourceLab",
            tables_allowlist=("dbo.Orders",), expected_columns={"dbo.Orders": ("Amount",)},
            require_encrypted_session="yes",
        )
