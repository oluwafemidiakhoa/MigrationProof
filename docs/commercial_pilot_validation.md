# MigrationProof — commercial-pilot validation gate

**Decision as of 2026-11-17: NO-GO for real customer databases.**

The integrated offline CLI smoke tests passed in GitHub Actions on `test/synthetic-cli-smoke-v1`, commit `001812832d42b1b3556714428bd7f14673c9590c` (workflow run 44204430475). This demonstrates a synthetic offline workflow. No live SQL Server integration test receipt or independently verified disposable lab host identity has been supplied.

## Generate current readiness assessment (no database connection)

```bash
python -m migrationproof.pilot_readiness_cli --output pilot-readiness.json
```

If a separately approved operator executes `scripts.run_sqlserver_lab_gate` on a disposable lab and retains the local receipt, optionally assess that *reported* receipt:

```bash
python -m migrationproof.pilot_readiness_cli --lab-receipt private-lab-receipt.json --output pilot-readiness-after-lab.json
```

The assessment always returns NO-GO while independent host identity, TLS certificate chain, least-privilege/metadata visibility, concurrent mutation behavior, bounded query plans, cross-database capture alignment, and customer authorization remain unverified. Local JSON alone cannot establish these facts.

## Lab acceptance checklist

1. **Environment authorization**: separate evidence of ownership and explicit approval for exact non-production host and disposable databases, not merely an approval string.
2. **Known fixture**: independently examine `docs/lab_source_target_demo.sql` on that host; only a designated operator may create its two disposable databases.
3. **TLS and identity**: observe the exact ODBC Driver 18 connection, server identity, and successful validation of the real certificate chain; no `TrustServerCertificate=yes`.
4. **Least privilege**: separately establish read-only rights and independent schema inventory; test missing metadata, row-level security and excess privileges.
5. **Expected error**: demonstrate mismatch on same row count, known synthetic source sum 150.00 versus target sum 1124.00, with a redacted execution receipt bound to commit and host.
6. **Isolation and concurrency**: verify SNAPSHOT mode in an authorized lab; measure transaction cleanup and row-version pressure under controlled concurrent synthetic updates.
7. **Resource bounds**: record query plan, CPU/IO, timeout behavior, locking, row budget and failure paths using disposable data.
8. **End-to-end evidence**: independently reproduce offline report and signature verification; separate evidence authenticity from mere SHA-256 integrity.
9. **Independent review and approval**: document outcomes, unresolved failures, privacy and commercial pilot scope; do not claim certification.

## Evidence retention and release boundaries

Save redacted, signed or independently authenticated evidence outside the public repository. Do not commit connection strings, secrets, customer records or private audit receipts. Green unit tests are not live integration acceptance. The readiness JSON is decision support, not a machine-authorized production release.

The recommended next action is to provision or identify a clearly authorized disposable SQL Server instance, execute the bounded lab runbook there, and supply the redacted receipts for independent analysis. Corporate SQL Server infrastructure must not be repurposed for this project without separate authorization.
