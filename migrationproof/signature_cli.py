"""Offline detached signature verification. Trusted keys come from a separate file."""
import argparse
import json
from pathlib import Path

from .evidence import EvidenceError
from .proof import ProofError, verify_proof
from .signatures import SignatureVerificationError, verify_detached_signature


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a scoped proof using an externally trusted Ed25519 key")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--signature", type=Path, required=True)
    parser.add_argument("--trusted-keys", type=Path, required=True,
                        help="Locally managed JSON map of trusted key IDs to base64 raw Ed25519 public keys")
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        envelope = json.loads(args.signature.read_text(encoding="utf-8"))
        trusted = json.loads(args.trusted_keys.read_text(encoding="utf-8"))
        signer = verify_detached_signature(manifest, envelope, trusted)
        report = verify_proof(args.root, manifest)
        print(f"VERIFIED: trusted_key={signer}; file-integrity=PASS; "
              f"recomputed_comparison=PASS; migration_decision={report['decision']}; "
              "database_completeness=INCOMPLETE")
        return 1 if report["decision"] == "DIFFERENCES_FOUND" else 0
    except (SignatureVerificationError, ProofError, EvidenceError,
            OSError, ValueError, TypeError, UnicodeError) as exc:
        print(f"VERIFICATION_FAILED/INCOMPLETE: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
