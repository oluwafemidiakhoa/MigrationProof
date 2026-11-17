"""Collect only approved non-production SQL Server tables with bounded reads."""
import argparse
import json
import os
from pathlib import Path
from .sqlserver import collect_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded experimental SQL Server collector")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--table", action="append", required=True,
                        help="Exact schema.table name to collect; repeatable")
    parser.add_argument("--snapshot-isolation", action="store_true",\n                        help="Opt in to per-database SNAPSHOT transaction; fails unless already enabled")\n    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--expected-columns", required=True, type=Path,
                        help="Independent JSON mapping schema.table to complete list of expected columns")
    parser.add_argument("--max-tables", type=int, default=10)
    parser.add_argument("--max-rows-per-table", type=int, default=10000)
    parser.add_argument("--sum-column", action="append", default=[],
                        help="Numeric column to sum in each collected table; repeatable")
    args = parser.parse_args()
    conn = os.environ.get("MIGRATIONPROOF_CONNECTION_STRING")
    if not conn:
        parser.error("Set MIGRATIONPROOF_CONNECTION_STRING in your local environment")
    if args.output.exists():
        parser.error("Output already exists; refusing overwrite")
    try:
        expected_columns = json.loads(args.expected_columns.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        parser.error("Cannot read expected column inventory")
    if not isinstance(expected_columns, dict):
        parser.error("Expected column inventory must be a JSON object")
    snapshot = collect_snapshot(
        conn, expected_database=args.expected_database,
        tables_allowlist=tuple(args.table),
        timeout=args.timeout,
        max_tables=args.max_tables,
        max_rows_per_table=args.max_rows_per_table,
        sum_columns=tuple(args.sum_column),
        expected_columns=expected_columns,\n        snapshot_isolation=args.snapshot_isolation,
    )
    args.output.write_text(snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(snapshot.tables)} explicitly scoped tables to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
