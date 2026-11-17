"""Assess source/target capture windows from offline JSON snapshots and receipts."""
import argparse
import json
from pathlib import Path

from .capture import CaptureEvidenceError, assess_capture_pair
from .core import DatabaseSnapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline capture-coherence assessor")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--source-receipt", required=True, type=Path)
    parser.add_argument("--target-receipt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.output.exists():
            parser.error("Output exists; refusing overwrite")
        left = DatabaseSnapshot.model_validate_json(args.source.read_text(encoding="utf-8"))
        right = DatabaseSnapshot.model_validate_json(args.target.read_text(encoding="utf-8"))
        source_receipt = json.loads(args.source_receipt.read_text(encoding="utf-8"))
        target_receipt = json.loads(args.target_receipt.read_text(encoding="utf-8"))
        report = assess_capture_pair(left, right, source_receipt, target_receipt)
        with args.output.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(f"Capture assessment: {report['decision']}; transactional coherence NOT_VERIFIED")
        return 1 if report["decision"] == "DIFFERENCES_FOUND" else 0
    except (OSError, ValueError, CaptureEvidenceError) as exc:
        # Never echo SQL connection strings; this module only handles offline files.
        print(f"INCOMPLETE: {type(exc).__name__}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
