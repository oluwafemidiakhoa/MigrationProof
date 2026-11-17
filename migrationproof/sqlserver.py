"""Optional read-only SQL Server metadata and explicitly requested aggregate collector."""
from __future__ import annotations
from contextlib import closing
from decimal import Decimal
from .core import DatabaseSnapshot, TableSnapshot

NUMERIC_TYPES = frozenset({
    "tinyint", "smallint", "int", "bigint", "decimal", "numeric",
    "money", "smallmoney", "float", "real"
})

def quote_identifier(value: str) -> str:
    if not value or "\x00" in value:
        raise ValueError("Invalid identifier")
    return "[" + value.replace("]", "]]") + "]"

def select_sum_columns(columns: dict[str, str], requested: tuple[str, ...]) -> tuple[str, ...]:
    """Reject unknown/non-numeric columns rather than silently skipping checks."""
    selected = []
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
    connection_string: str, *, timeout: int = 15, max_tables: int = 100,
    sum_columns: tuple[str, ...] = (),
) -> DatabaseSnapshot:
    """Read metadata, exact row counts, and opt-in sums from approved lab databases.

    All requested aggregate columns must exist and be numeric in every selected
    table. Errors abort collection rather than producing an incomplete success.
    """
    if not 1 <= timeout <= 300 or not 1 <= max_tables <= 1000:
        raise ValueError("Invalid limits")
    try:
        import pyodbc
    except ImportError as exc:
        raise RuntimeError("Install pyodbc first") from exc
    with closing(pyodbc.connect(connection_string, timeout=timeout, autocommit=True, readonly=True)) as conn:
        conn.timeout = timeout
        cur = conn.cursor()
        cur.execute("SELECT DB_NAME()")
        database = str(cur.fetchone()[0])
        cur.execute("""SELECT s.name, t.name, c.name, ty.name, c.max_length, c.precision, c.scale, c.is_nullable
            FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
            JOIN sys.columns c ON c.object_id=t.object_id
            JOIN sys.types ty ON ty.user_type_id=c.user_type_id
            WHERE t.is_ms_shipped=0 ORDER BY s.name,t.name,c.column_id""")
        metadata = {}
        for schema, table, column, typ, length, precision, scale, nullable in cur:
            metadata.setdefault((schema, table), {})[column] = f"{typ}({length},{precision},{scale}) NULL={bool(nullable)}"
        if len(metadata) > max_tables:
            raise ValueError("Table limit exceeded")
        tables = {}
        for (schema, table), columns in metadata.items():
            selected = select_sum_columns(columns, sum_columns)
            table_name = f"{quote_identifier(schema)}.{quote_identifier(table)}"
            cur.execute(f"SELECT COUNT_BIG(*) FROM {table_name}")
            row_count = int(cur.fetchone()[0])
            aggregates = {}
            for column in selected:
                cur.execute(f"SELECT SUM({quote_identifier(column)}) FROM {table_name}")
                value = cur.fetchone()[0]
                # Decimal is serialized as a string to avoid floating-point rounding.
                aggregates[f"sum:{column}"] = str(value) if isinstance(value, Decimal) else value
            tables[f"{schema}.{table}"] = TableSnapshot(
                columns=columns, row_count=row_count, aggregates=aggregates
            )
        return DatabaseSnapshot(database=database, tables=tables)
