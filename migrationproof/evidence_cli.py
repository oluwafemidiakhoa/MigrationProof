"""Offline evidence bundle manifest CLI, no database or network access."""
import argparse
import json
from pathlib import Path

from .evidence import EvidenceError, build_manifest, dumps_manifest, verify_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify file-integrity evidence manifests")
    subs = parser.add_subparsers(dest="command", required=True)
    create = subs.add_parser("create", help="Write manifest for explicitly selected files")
    create.add_argument("--root", required=True, type=Path)
    create.add_argument("--file", action="append", dest="files", required=True)
    create.add_argument("--output", required=True, type=Path)
    verify = subs.add_parser("verify", help="Check manifest against files on disk")
    verify.add_argument("--root", required=True, type=Path)
    verify.add_argument("--manifest", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "create":
            if args.output.exists():
                parser.error("Output exists; refusing overwrite")
            root = args.root.resolve(strict=True)
            output = args.output.resolve()
            if output == root or root in output.parents:
                parser.error("Write manifest outside evidence root to avoid self-reference")
            manifest = build_manifest(root, args.files)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(dumps_manifest(manifest))
            print("Manifest created (file integrity only; not signed or authenticated)")
            return 0
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        verify_manifest(args.root, manifest)
        print("PASS: selected evidence file bytes match manifest; authenticity is NOT verified")
        return 0
    except (EvidenceError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"INCOMPLETE/FAIL: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
