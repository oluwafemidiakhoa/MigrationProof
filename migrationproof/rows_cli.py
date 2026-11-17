"""Offline keyed-row reconciliation CLI (no database/network access)."""
import argparse
import json
from pathlib import Path

from .rows import RowEvidenceError, reconcile_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare sanitized, explicitly supplied keyed rows")
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.output and args.output.exists():
            parser.error("Output exists; refusing overwrite")
        source = json.loads(args.source.read_text(encoding="utf-8"))
        target = json.loads(args.target.read_text(encoding="utf-8"))
        report = reconcile_rows(source, target)
        result = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.write_text(result, encoding="utf-8")
        else:
            print(result, end="")
        return 1 if report["status"] == "DIFFERENCES_FOUND" else 0
    except (RowEvidenceError, OSError, ValueError) as error:
        parser.exit(2, f"INCOMPLETE: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
