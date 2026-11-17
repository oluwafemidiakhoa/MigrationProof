"""Verify externally produced Ed25519 detached signatures over canonical manifests.

Trust anchors must be supplied out-of-band by the verifier. The evidence
producer cannot self-assert who is trusted. No signing keys are handled here.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from .evidence import EvidenceError, dumps_manifest

SIGNATURE_FORMAT = "migrationproof.detached-signature.v1"
MAX_MANIFEST_BYTES = 2 * 1024 * 1024


class SignatureVerificationError(ValueError):
    """Detached signature malformed, untrusted, or invalid."""


def canonical_manifest_bytes(manifest: dict[str, Any]) -> bytes:
    if not isinstance(manifest, dict):
        raise SignatureVerificationError("Manifest must be a JSON object")
    try:
        payload = dumps_manifest(manifest).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise SignatureVerificationError("Manifest cannot be canonicalized") from exc
    if len(payload) > MAX_MANIFEST_BYTES:
        raise SignatureVerificationError("Manifest exceeds verification limit")
    return payload


def _decode_base64(value: Any, length: int) -> bytes:
    if not isinstance(value, str) or len(value) > 200:
        raise SignatureVerificationError("Invalid base64 field")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise SignatureVerificationError("Invalid base64 encoding") from exc
    if len(raw) != length or base64.b64encode(raw).decode("ascii") != value:
        raise SignatureVerificationError("Invalid base64 length or canonical encoding")
    return raw


def verify_detached_signature(
    manifest: dict[str, Any],
    envelope: dict[str, Any],
    trusted_public_keys: dict[str, str],
) -> str:
    """Return trusted signer label only after Ed25519 verification succeeds.

    trusted_public_keys: map of externally approved key labels -> base64 raw
    32-byte Ed25519 public keys. Do not fetch keys from envelope metadata.
    """
    if not isinstance(envelope, dict) or set(envelope) != {
        "format", "algorithm", "key_id", "manifest_sha256", "signature_b64"
    }:
        raise SignatureVerificationError("Invalid detached signature envelope")
    if envelope["format"] != SIGNATURE_FORMAT or envelope["algorithm"] != "Ed25519":
        raise SignatureVerificationError("Unsupported signature format or algorithm")
    key_id = envelope["key_id"]
    if not isinstance(key_id, str) or not key_id or len(key_id) > 128:
        raise SignatureVerificationError("Invalid signer key id")
    if not isinstance(trusted_public_keys, dict) or key_id not in trusted_public_keys:
        raise SignatureVerificationError("Signer is not on the external trust list")
    manifest_bytes = canonical_manifest_bytes(manifest)
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    if envelope["manifest_sha256"] != digest:
        raise SignatureVerificationError("Manifest digest mismatch")
    public_bytes = _decode_base64(trusted_public_keys[key_id], 32)
    signature = _decode_base64(envelope["signature_b64"], 64)
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise SignatureVerificationError(
            "Install the [signatures] extra to verify Ed25519 evidence"
        ) from exc
    try:
        Ed25519PublicKey.from_public_bytes(public_bytes).verify(signature, manifest_bytes)
    except (InvalidSignature, ValueError) as exc:
        raise SignatureVerificationError("Detached signature verification failed") from exc
    return key_id
