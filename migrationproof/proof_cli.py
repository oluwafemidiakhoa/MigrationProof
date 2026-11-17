"""Create or verify a scoped, unsigned offline MigrationProof evidence bundle."""
import argparse
import json
from pathlib import Path

from .evidence import dumps_manifest
from .proof import ProofError, create_proof, finalize_manifest, verify_proof


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline scoped proof bundle")
    subs = parser.add_subparsers(dest="command", required=True)
    create = subs.add_parser("create")
    create.add_argument("--root", type=Path, required=True,
                        help="Evidence folder containing source_rows.json and target_rows.json")
    create.add_argument("--manifest", type=Path, required=True,
                        help="Manifest path outside evidence root")
    verify = subs.add_parser("verify")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        manifest_path = args.manifest.resolve()
        if args.command == "create":
            if root == manifest_path or root in manifest_path.parents:
                raise ProofError("Manifest must be outside the evidence directory")
            if args.manifest.exists():
                raise ProofError("Manifest already exists")
            report = create_proof(root)
            report_path = root / "comparison.json"
            with report_path.open("x", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, sort_keys=True)
                handle.write("\n")
            manifest = finalize_manifest(root)
            with args.manifest.open("x", encoding="utf-8") as handle:
                handle.write(dumps_manifest(manifest))
            print(f"{report['decision']}: unsigned offline report and manifest created")
            return 1 if report["decision"] == "DIFFERENCES_FOUND" else 0
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        report = verify_proof(root, manifest)
        print(f"VERIFIED_FILE_INTEGRITY; migration decision={report['decision']}; authenticity=NOT_TESTED")
        return 1 if report["decision"] == "DIFFERENCES_FOUND" else 0
    except (ProofError, OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"INCOMPLETE: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
