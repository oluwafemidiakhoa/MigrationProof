"""Query-shape regression tests: never run separate unbounded SUM scans."""
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
    def __init__(self, count):
        self.count = count
        self.queries = []
        self.rows = []

    def execute(self, query):
        self.queries.append(query)
        if query == "SELECT DB_NAME()":
            self.rows = [("MigrationProofSourceLab",)]
        elif "FROM sys.tables" in query:
            self.rows = [
                ("dbo", "Orders", "OrderID", "int", 4, 10, 0, False),
                ("dbo", "Orders", "Amount", "decimal", 9, 12, 2, False),
            ]
        elif "FROM [dbo].[Orders]" in query:
            if "TOP (4)" not in query:
                raise AssertionError("Table read is not bounded")
            if "SUM([Amount])" not in query or "COUNT_BIG(*)" not in query:
                raise AssertionError("Aggregate and bounded count must share one query")
            self.rows = [(self.count, "150.00")]
        else:
            raise AssertionError("Unexpected SQL query")
        return self

    def __iter__(self):
        return iter(self.rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None


class Connection:
    def __init__(self, count):
        self.cursor_object = Cursor(count)
        self.timeout = None

    def cursor(self):
        return self.cursor_object

    def close(self):
        pass


def snapshot(monkeypatch, count):
    connection = Connection(count)
    monkeypatch.setitem(
        sys.modules, "pyodbc",
        SimpleNamespace(connect=lambda *args, **kwargs: connection),
    )
    result = None
    try:
        result = collect_snapshot(
            CONNECTION,
            expected_database="MigrationProofSourceLab",
            tables_allowlist=("dbo.Orders",),
            expected_columns={"dbo.Orders": ("OrderID", "Amount")},
            max_rows_per_table=3,
            max_tables=1,
            sum_columns=("Amount",),
        )
    finally:
        # Even when the limit is hit, the single bounded SQL query is the only
        # table-data query executed.
        reads = [
            query for query in connection.cursor_object.queries
            if "FROM [dbo].[Orders]" in query
        ]
        assert len(reads) == 1
        assert reads[0].count("FROM [dbo].[Orders]") == 1
    return result


def test_bounded_count_and_sum_in_single_query(monkeypatch):
    result = snapshot(monkeypatch, 3)
    assert result.tables["dbo.Orders"].row_count == 3
    assert result.tables["dbo.Orders"].aggregates["sum:Amount"] == "150.00"


def test_oversized_table_fails_closed_without_unbounded_followup(monkeypatch):
    with pytest.raises(ValueError, match="Row budget exceeded"):
        snapshot(monkeypatch, 4)
