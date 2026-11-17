# Detached Ed25519 signature verification — experimental

This module verifies a previously created scoped-proof manifest with an **out-of-band trusted Ed25519 public key**. It then verifies the evidence files and reproduces the comparison. Signing itself is **not implemented**, and no private keys should be stored in this repository.

## Trust model

An attacker controlling both a manifest and its unsigned files can replace both without detection. Detached signatures are an improvement **only if the verifying party receives and validates the signer's public key through a separate trusted channel**. The signature envelope must not dictate trusted identity, and its key_id is only a lookup label. Independent reviewer enrollment, revocation, signed release provenance, trusted timestamps and identity governance remain missing.

## Verification

Install the optional cryptography dependency:

```bash
python -m pip install -e ".[signatures]"
```

Have an approved signatory issue a detached envelope over **the exact ASCII bytes** from `canonical_manifest_bytes(manifest)`. The signature envelope schema is:

```json
{
  "format": "migrationproof.detached-signature.v1",
  "algorithm": "Ed25519",
  "key_id": "approved-signer",
  "manifest_sha256": "64 lowercase hex characters",
  "signature_b64": "canonical base64 of the raw 64-byte Ed25519 signature"
}
```

The separately administered `trusted-keys.json` file contains a mapping of `key_id` to base64-encoded raw 32-byte public keys. This trust file must be provisioned independently, protected from untrusted bundle writers, and verified operationally.

Then execute:

```bash
python -m migrationproof.signature_cli --root sample-evidence \
    --manifest sample-manifest.json \
    --signature detached-signature.json \
    --trusted-keys trusted-keys.json
```

Return codes: 0 = verified signature, integrity and computation, with migration decision **INCOMPLETE**; 1 = verified signature and computation with **DIFFERENCES_FOUND**; 2 = verification failed or incomplete. Return 0 is **not a production certification**.

## Boundaries

- No network, database access, key creation, signer enrollment, signing, identity certification or deployment.
- SHA-256 manifest and Ed25519 signature authenticity depend on the correct trusted key distribution.
- A valid signature only proves a holder of the corresponding private key signed the manifest, not that its database observations are honest, complete or timely.
- Avoid printing secret/customer data in errors; run verification on approved sanitized evidence.
- Validate this workflow with reproducible unit tests and independent offline reviewer testing before any commercial claim.
