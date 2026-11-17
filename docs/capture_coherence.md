# Offline capture coherence assessment

The assessor checks **operator-supplied**, digest-bound snapshot capture windows. It does not collect from SQL Server, attest operator identity, prove trusted clocks, or establish SQL transaction isolation.

Provide source and target snapshot JSON files following the existing DatabaseSnapshot schema. For each, independently record the following receipt alongside the corresponding snapshot:

```json
{
  "format": "migrationproof.capture-receipt.v1",
  "database": "SourceLab",
  "snapshot_sha256": "<actual canonical_digest of the associated snapshot>",
  "capture_started_at": "2026-11-17T12:00:00Z",
  "capture_finished_at": "2026-11-17T12:00:02Z",
  "transaction_consistency": "NOT_TESTED",
  "clock_trust": "NOT_TESTED"
}
```

Run:

```bash
python -m migrationproof.capture_cli --source source.json --target target.json --source-receipt source-receipt.json --target-receipt target-receipt.json --output capture-assessment.json
```

Output is deterministic given the supplied evidence and refuses overwrite. Reversed and overlong windows, mismatched snapshot digests, unsupported transaction-isolation claims, and unknown fields are rejected.

A matching comparison produces **INCOMPLETE**, never migration PASS. A discrepancy produces **DIFFERENCES_FOUND**. Disjoint capture windows or start-time skew over the fixed policy are flagged. Even overlapping windows do **not** establish a shared database state, absence of concurrent updates, or trusted clocks.

**This is not a trusted timestamp or transactionally consistent SQL Server capture implementation.** The current SQL collector does not issue or verify trusted transaction snapshots. Only an independent, authorized disposable SQL Server test with separately verified isolation and source provenance can promote those claims. No production or customer database should be used for this test.
