"""Offline pilot-readiness report CLI (never runs SQL or grants approval)."""
import argparse
import json
from pathlib import Path

from .pilot_readiness import canonical_report, evaluate_pre_pilot


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate evidence for a commercial pilot (fail closed)")
    parser.add_argument("--lab-receipt", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; refusing overwrite")
    try:
        receipt = None
        if args.lab_receipt is not None:
            if args.lab_receipt.stat().st_size > 64 * 1024:
                raise ValueError("Receipt exceeds input budget")
            receipt = json.loads(args.lab_receipt.read_text(encoding="utf-8"))
        report = evaluate_pre_pilot(receipt)
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(canonical_report(report))
        print("NO_GO: pilot release blockers remain; see saved assessment")
        return 2
    except (OSError, ValueError, UnicodeError):
        print("INCOMPLETE: evidence could not be assessed")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
