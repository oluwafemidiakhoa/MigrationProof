import base64
import hashlib

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from migrationproof.evidence import build_manifest
from migrationproof.signatures import (
    SIGNATURE_FORMAT,
    SignatureVerificationError,
    canonical_manifest_bytes,
    verify_detached_signature,
)


def fixture(tmp_path):
    (tmp_path / "sample.txt").write_text("synthetic", encoding="utf-8")
    manifest = build_manifest(tmp_path, ["sample.txt"])
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    payload = canonical_manifest_bytes(manifest)
    envelope = {
        "format": SIGNATURE_FORMAT,
        "algorithm": "Ed25519",
        "key_id": "test-operator-1",
        "manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "signature_b64": base64.b64encode(private_key.sign(payload)).decode("ascii"),
    }
    trusted = {"test-operator-1": base64.b64encode(public_key).decode("ascii")}
    return manifest, envelope, trusted


def test_valid_external_trust_anchor(tmp_path):
    manifest, envelope, trusted = fixture(tmp_path)
    assert verify_detached_signature(manifest, envelope, trusted) == "test-operator-1"


def test_changed_manifest_rejected(tmp_path):
    manifest, envelope, trusted = fixture(tmp_path)
    manifest["scope"] = "tampered"
    with pytest.raises(SignatureVerificationError, match="digest mismatch"):
        verify_detached_signature(manifest, envelope, trusted)


def test_signature_modified_rejected(tmp_path):
    manifest, envelope, trusted = fixture(tmp_path)
    envelope["signature_b64"] = base64.b64encode(bytes(64)).decode("ascii")
    with pytest.raises(SignatureVerificationError, match="signature verification failed"):
        verify_detached_signature(manifest, envelope, trusted)


def test_untrusted_signer_rejected(tmp_path):
    manifest, envelope, trusted = fixture(tmp_path)
    with pytest.raises(SignatureVerificationError, match="external trust list"):
        verify_detached_signature(manifest, envelope, {})


def test_key_substitution_rejected(tmp_path):
    manifest, envelope, trusted = fixture(tmp_path)
    other = Ed25519PrivateKey.generate().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    trusted["test-operator-1"] = base64.b64encode(other).decode("ascii")
    with pytest.raises(SignatureVerificationError, match="verification failed"):
        verify_detached_signature(manifest, envelope, trusted)


@pytest.mark.parametrize("changed", [
    {"algorithm": "none"},
    {"format": "unknown"},
    {"key_id": "different"},
    {"signature_b64": "not-base64"},
    {"manifest_sha256": "a" * 64},
])
def test_invalid_envelopes_rejected(tmp_path, changed):
    manifest, envelope, trusted = fixture(tmp_path)
    envelope.update(changed)
    with pytest.raises(SignatureVerificationError):
        verify_detached_signature(manifest, envelope, trusted)


def test_envelope_with_injected_public_key_rejected(tmp_path):
    manifest, envelope, trusted = fixture(tmp_path)
    envelope["public_key"] = trusted["test-operator-1"]
    with pytest.raises(SignatureVerificationError, match="envelope"):
        verify_detached_signature(manifest, envelope, trusted)
