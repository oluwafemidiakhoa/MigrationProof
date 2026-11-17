# Scoped Offline Proof Bundle v1

This experimental module combines the previous two independent features:
* offline keyed-row comparison;
* SHA-256 manifests over selected evidence files.

It intentionally **does not** certify migration accuracy, data completeness, customer authorization, real-time collection consistency or signer identity.

## Operator flow

Put previously sanitized, approved offline inputs in a fresh folder:

```text
sample-evidence/
  source_rows.json
  target_rows.json
```

Use the schema described in [row_reconciliation.md](row_reconciliation.md). Then:

```bash
python -m migrationproof.proof_cli create --root sample-evidence --manifest sample-manifest.json
python -m migrationproof.proof_cli verify --root sample-evidence --manifest sample-manifest.json
```

The `create` command exclusively creates `sample-evidence/comparison.json` and the manifest outside the evidence root. Both refuse overwrite. The manifest covers exactly `comparison.json`, `source_rows.json`, and `target_rows.json`. The verification path recomputes row-level results from the inputs and checks every file digest, detecting report tampering even if an attacker simply rehashes a falsified report.

## Report semantics

* `DIFFERENCES_FOUND`: tested keyed rows differ.
* `INCOMPLETE`: tested keyed rows agree but the completeness and collection consistency requirements are not established.
* Malformed input/missing/altered files: process returns error/incomplete.

Exit codes: 0 means operation succeeded with **INCOMPLETE** migration decision; 1 means successful comparison with **DIFFERENCES_FOUND**; 2 means an incomplete or failed operation.

The comparison never generates an overall `PASS` because row selection and database coverage are not independently established. Digest verification proves local file integrity and reproducible calculations, **not source authenticity**. A party with access to rewrite the input evidence and manifest can still fabricate input data; add an independently controlled digital signature and verified collection receipts before customer assurance use.

## Additional limitations

This package operates only on supplied sanitized JSON; all row values remain inside local input files. It does not query SQL Server, implement a database permissions model, securely sign manifests, provide whole-table consistency, prove row coverage, or protect against hostile filesystem race conditions. Keep customer information out of demos and Git history.

## Development gates

1. CI tests on the exact branch/commit;
2. explicit test cases for equal count/sum but different keyed values;
3. negative path and tampering tests;
4. independent reproducibility test on an isolated workstation;
5. before any real database: approved scoped read-only collector integration, TLS validation and capture-completeness testing;
6. before any commercial verification: signer identity, source provenance, privacy and retention controls, independent reviewer.
