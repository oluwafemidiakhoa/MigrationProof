"""Offline CLI: python -m migrationproof.cli source.json target.json --output report.json"""
import argparse
import json
from pathlib import Path

from .core import DatabaseSnapshot, reconcile


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline migration snapshot reconciliation")
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = DatabaseSnapshot.model_validate_json(args.source.read_text(encoding="utf-8"))
    target = DatabaseSnapshot.model_validate_json(args.target.read_text(encoding="utf-8"))
    report = reconcile(source, target)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 1 if report["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
