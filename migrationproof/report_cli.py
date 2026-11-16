"""Render an existing reconciliation report as HTML."""
import argparse
import json
from pathlib import Path
from .html_report import render_html

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; refusing overwrite")
    args.output.write_text(render_html(json.loads(args.report.read_text(encoding="utf-8"))), encoding="utf-8")
    print(f"Saved HTML report: {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
