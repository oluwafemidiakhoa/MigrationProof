# Offline evidence integrity (experimental)

MigrationProof can produce a deterministic SHA-256 manifest for selected report and snapshot files, then detect whether file bytes changed.

**This is an integrity check only. It is NOT a digital signature, trusted timestamp, verification of database accuracy, full completeness attestation, or migration certificate.** A party able to replace both manifest and evidence can make them agree again. Treat unsigned manifests as locally useful but unauthenticated.

## Example

Use an already generated local report and sanitized snapshots:

```bash
python -m migrationproof.evidence_cli create \
  --root ./evidence \
  --file source.json --file target.json --file report.json \
  --output manifest.json
python -m migrationproof.evidence_cli verify --root ./evidence --manifest manifest.json
```

The output manifest MUST be written outside the evidence root to avoid self-reference. Paths passed to `--file` are relative paths below the evidence root, not absolute paths. No database or network access is performed.

`create` refuses to overwrite an existing manifest. `verify` returns exit 0 on exact byte equality, and exit 2 if verification cannot be completed or detects a mismatch.

## Guardrails and limitations

- Explicit file selection and nonempty, unique sorted path set.
- Per-file cap: 128 MiB; at most 1,000 files; chunked read.
- Rejects traversal, absolute paths, Windows drive notation, symlinks and missing files.
- Verifies byte-level SHA-256 and file lengths. It does not enumerate unlisted files or prove all required evidence was captured.
- The canonical manifest can later be signed externally using an audited signing service. Do not claim signing is implemented here.
- Check/time-of-use races and filesystem-level adversaries require stronger OS-level file descriptor and permission controls for a hostile local environment.
- Preserve sanitized evidence and never commit actual customer data or reports.

## Planned signed-proof extension

After the evidence format and authorization model stabilize, add protected signing identity and offline verification of a signed manifest. Bind signer, source/target identity, code revision, collection timestamps, query scope, row-level coverage, completeness and approved policy to the signed claim.
