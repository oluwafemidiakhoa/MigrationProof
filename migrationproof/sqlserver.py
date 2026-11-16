"""Optional read-only SQL Server metadata collector."""
from __future__ import annotations
from contextlib import closing
from .core import DatabaseSnapshot, TableSnapshot

def quote_identifier(value: str) -> str:
    if not value or "\x00" in value:
        raise ValueError("Invalid identifier")
    return "[" + value.replace("]", "]]") + "]"

def collect_snapshot(connection_string: str, *, timeout: int = 15, max_tables: int = 100) -> DatabaseSnapshot:
    """Metadata and COUNT_BIG for bounded tables. Use only on approved test databases."""
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
            cur.execute(f"SELECT COUNT_BIG(*) FROM {quote_identifier(schema)}.{quote_identifier(table)}")
            tables[f"{schema}.{table}"] = TableSnapshot(columns=columns, row_count=int(cur.fetchone()[0]))
        return DatabaseSnapshot(database=database, tables=tables)
