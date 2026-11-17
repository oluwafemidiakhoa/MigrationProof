"""Bounded, read-only SQL Server snapshot collector for authorized test databases.

This collector proves checks only over explicitly named tables. It does not prove
whole-database equivalence or a transactionally consistent point-in-time view.
"""
from __future__ import annotations

from contextlib import closing
from decimal import Decimal
import re

from .core import DatabaseSnapshot, TableSnapshot

NUMERIC_TYPES = frozenset({
    "tinyint", "smallint", "int", "bigint", "decimal", "numeric",
    "money", "smallmoney", "float", "real",
})
SYSTEM_DATABASES = frozenset({"master", "model", "msdb", "tempdb"})


def quote_identifier(value: str) -> str:
    if not value or "\x00" in value:
        raise ValueError("Invalid identifier")
    return "[" + value.replace("]", "]]") + "]"


def validate_connection_security(connection_string: str) -> None:
    """Conservative defense-in-depth check; ODBC driver still enforces TLS."""
    # Refuse ambiguous duplicate security keys rather than let driver precedence vary.
    parts = [part.strip() for part in connection_string.split(";") if part.strip()]
    options: dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            raise ValueError("Malformed ODBC connection string")
        key, value = part.split("=", 1)
        key = re.sub(r"\s+", "", key).lower()
        if key in options:
            raise ValueError("Duplicate connection-string option")
        options[key] = value.strip().lower()
    if options.get("encrypt") not in {"yes", "true", "mandatory", "strict"}:
        raise ValueError("Encrypted SQL connection is required")
    if options.get("trustservercertificate") not in {"no", "false"}:
        raise ValueError("TrustServerCertificate=no is required")
    if "database" not in options and "initialcatalog" not in options:
        raise ValueError("Explicit database required")
    if any(key in options for key in ("uid", "user", "user id", "pwd", "password")):
        # Password-bearing strings may be valid, but avoid parsing/reprinting them.
        # Never include the connection string in an exception.
        raise ValueError("Use a scoped integrated or externally managed identity")


def select_sum_columns(columns: dict[str, str], requested: tuple[str, ...]) -> tuple[str, ...]:
    selected: list[str] = []
    for name in requested:
        if name not in columns:
            raise ValueError(f"Requested aggregate column not found: {name}")
        datatype = columns[name].split("(", 1)[0].lower()
        if datatype not in NUMERIC_TYPES:
            raise ValueError(f"Requested aggregate column is not numeric: {name}")
        if name not in selected:
            selected.append(name)
    return tuple(selected)


def collect_snapshot(
    connection_string: str, *,
    expected_database: str,
    tables_allowlist: tuple[str, ...],
    timeout: int = 15,
    max_tables: int = 10,
    max_rows_per_table: int = 10000,
    sum_columns: tuple[str, ...] = (),
    expected_columns: dict[str, tuple[str, ...]] | None = None,
    snapshot_isolation: bool = False,
) -> DatabaseSnapshot:
    """Collect bounded exact counts and opt-in sums only for named tables.

    Failure to verify scope, the independently supplied column inventory, or
    enforce a row limit aborts the entire collection.
    Do not use on production. Source/target point-in-time consistency is unproven.
    """
    if type(snapshot_isolation) is not bool:
        raise ValueError("snapshot_isolation must be a boolean")
    if not 1 <= timeout <= 60 or not 1 <= max_tables <= 100 or not 1 <= max_rows_per_table <= 100000:
        raise ValueError("Collection limits outside approved bounds")
    if not expected_database or expected_database.lower() in SYSTEM_DATABASES:
        raise ValueError("An approved non-system database name is required")
    if not tables_allowlist or len(set(tables_allowlist)) != len(tables_allowlist):
        raise ValueError("A nonempty, duplicate-free table allowlist is required")
    if len(tables_allowlist) > max_tables:
        raise ValueError("Table allowlist exceeds max_tables")
    requested_names = set(tables_allowlist)
    if any(name.count(".") != 1 or not all(name.split(".")) for name in requested_names):
        raise ValueError("Table names must be exact schema.table names")
    if expected_columns is None or set(expected_columns) != requested_names:
        raise ValueError("Independent expected-column inventory required for every allowed table")
    for table_name, expected in expected_columns.items():
        if not isinstance(expected, (tuple, list)) or not expected or any(
            not isinstance(name, str) or not name for name in expected
        ) or len(expected) != len(set(expected)):
            raise ValueError("Invalid independent expected-column inventory")
    validate_connection_security(connection_string)
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError("Install pyodbc first") from exc
    with closing(pyodbc.connect(connection_string, timeout=timeout, autocommit=True, readonly=True)) as conn:
        conn.timeout = timeout
        cur = conn.cursor()
        if snapshot_isolation:
            # Preflight verifies the database is already configured by an
            # authorized DBA. Collector never changes database settings.
            cur.execute(
                "SELECT snapshot_isolation_state FROM sys.databases "
                "WHERE database_id = DB_ID()"
            )
            row = cur.fetchone()
            if row is None or int(row[0]) != 1:
                raise ValueError("SNAPSHOT isolation is not enabled in this database")
            # Explicit transaction works even with the pyodbc connection's
            # autocommit=True; it must be rolled back on every exit path.
            cur.execute("SET TRANSACTION ISOLATION LEVEL SNAPSHOT")
            cur.execute("BEGIN TRANSACTION")
        try:
            return _read_allowed_tables(
                cur, expected_database, requested_names, expected_columns,
                max_rows_per_table, sum_columns
            )
        finally:
            if snapshot_isolation:
                cur.execute("IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION")


def _read_allowed_tables(
    cur, expected_database: str, requested_names: set[str],
    expected_columns: dict[str, tuple[str, ...]],
    max_rows_per_table: int, sum_columns: tuple[str, ...],
) -> DatabaseSnapshot:
    """All metadata and data reads execute inside the same opted-in transaction."""
    cur.execute("SELECT DB_NAME()")
    observed_db = str(cur.fetchone()[0])
    if observed_db != expected_database:
        raise ValueError("Connected database does not match approved expected_database")
    cur.execute("""SELECT s.name, t.name, c.name, ty.name, c.max_length, c.precision, c.scale, c.is_nullable
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.columns c ON c.object_id=t.object_id
        JOIN sys.types ty ON ty.user_type_id=c.user_type_id
        WHERE t.is_ms_shipped=0 ORDER BY s.name,t.name,c.column_id""")
    metadata: dict[tuple[str, str], dict[str, str]] = {}
    for schema, table, column, typ, length, precision, scale, nullable in cur:
        full_name = f"{schema}.{table}"
        if full_name in requested_names:
            metadata.setdefault((schema, table), {})[column] = (
                f"{typ}({length},{precision},{scale}) NULL={bool(nullable)}"
            )
    observed_names = {f"{schema}.{table}" for schema, table in metadata}
    if observed_names != requested_names:
        raise ValueError("One or more expected tables are not visible; collection incomplete")
    for (schema, table), columns in metadata.items():
        full_name = f"{schema}.{table}"
        if set(columns) != set(expected_columns[full_name]):
            raise ValueError("Column inventory mismatch; collection incomplete")
    tables: dict[str, TableSnapshot] = {}
    for (schema, table), columns in sorted(metadata.items()):
        selected = select_sum_columns(columns, sum_columns)
        qualified = f"{quote_identifier(schema)}.{quote_identifier(table)}"
        # Count and all optional sums are computed from ONE bounded input.
        # If TOP(N+1) sees the overflow row, no aggregate result is trusted.
        # This avoids a separate, potentially unbounded SUM scan.
        bound = max_rows_per_table + 1
        projected = ", ".join(quote_identifier(name) for name in selected)
        if not projected:
            projected = "1 AS [_marker]"
        expressions = ["COUNT_BIG(*)"] + [
            f"SUM({quote_identifier(name)})" for name in selected
        ]
        query = (
            f"SELECT {', '.join(expressions)} FROM "
            f"(SELECT TOP ({bound}) {projected} FROM {qualified}) AS bounded"
        )
        cur.execute(query)
        result = cur.fetchone()
        if result is None:
            raise ValueError("Aggregate query returned no result; collection incomplete")
        count = int(result[0])
        if count > max_rows_per_table:
            raise ValueError("Row budget exceeded; collection incomplete")
        aggregates = {}
        for index, column in enumerate(selected, start=1):
            value = result[index]
            aggregates[f"sum:{column}"] = (
                str(value) if isinstance(value, Decimal) else value
            )
        tables[f"{schema}.{table}"] = TableSnapshot(
            columns=columns, row_count=count, aggregates=aggregates
        )
    return DatabaseSnapshot(database=observed_db, tables=tables)
