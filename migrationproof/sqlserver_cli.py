"""Collect a snapshot with credentials supplied only through an environment variable."""
import argparse
import os
from pathlib import Path
from .sqlserver import collect_snapshot

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--max-tables", type=int, default=100)
    parser.add_argument("--sum-column", action="append", default=[],
                        help="Numeric column to sum in every collected table; repeatable")
    args = parser.parse_args()
    conn = os.environ.get("MIGRATIONPROOF_CONNECTION_STRING")
    if not conn:
        parser.error("Set MIGRATIONPROOF_CONNECTION_STRING in your local environment")
    if args.output.exists():
        parser.error("Output already exists; refusing overwrite")
    snapshot = collect_snapshot(
        conn, timeout=args.timeout, max_tables=args.max_tables,
        sum_columns=tuple(args.sum_column)
    )
    args.output.write_text(snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(snapshot.tables)} tables to {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
