# Independent SQL Server lab reconciliation — v0.3

**Purpose:** demonstrate detection of a changed value even when row counts match. This is not customer validation or proof of row-level equivalence.

## Safety gate

- Use only an explicitly approved nonproduction SQL Server environment and two NEW disposable databases.
- The SQL setup script creates databases and inserts/updates **synthetic test data**. Review and execute manually in SSMS only after confirming server ownership, capacity, and change requirements.
- Never run the setup script on a business production instance.
- The Python collector only reads; it requires explicitly allowed tables, a bounded TOP-based count, and an optional SUM (which may still consume resources).
- Use a dedicated read-only principal for customer pilots. Use a dedicated read-only identity and verified TLS; certificate bypass is not accepted.
- Source and target snapshots are collected independently; do not copy one JSON file to the other.
- Don't commit snapshots containing customer metadata.

## Lab setup

Open `docs/lab_source_target_demo.sql` in SSMS and review it. Execute only on an approved nonproduction instance.

Before collecting, use an independently reviewed `approved_lab_columns.json` matching the complete `dbo.Orders` column list. The list cannot be inferred from the same restricted collector; inspect and confirm it separately using an authorized inventory account.\n\n## Collect on Windows (Command Prompt, active .venv)

Use your approved SQL Server hostname in place of LAB_SERVER. Use an appropriate trusted certificate and Driver 18 for a production-like test. Certificate validation must remain enabled.

```bat
set "MIGRATIONPROOF_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=LAB_SERVER;DATABASE=MigrationProofSourceLab;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=no;"
python -m migrationproof.sqlserver_cli --output source_lab.json --expected-database MigrationProofSourceLab --table dbo.Orders --expected-columns approved_lab_columns.json --max-tables 2 --max-rows-per-table 1000 --sum-column Amount

set "MIGRATIONPROOF_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=LAB_SERVER;DATABASE=MigrationProofTargetLab;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=no;"
python -m migrationproof.sqlserver_cli --output target_lab.json --expected-database MigrationProofTargetLab --table dbo.Orders --expected-columns approved_lab_columns.json --max-tables 2 --max-rows-per-table 1000 --sum-column Amount

python -m migrationproof.cli source_lab.json target_lab.json --output lab_report.json
python -m migrationproof.report_cli lab_report.json --output lab_report.html
start lab_report.html
```

The reconciliation command intentionally exits 1 on differences. Expected finding: `AGGREGATE_MISMATCH` for `sum:Amount`, with both row counts 3.

## Interpretation and remaining hardening

- Equal row counts and equal sums do not establish row equivalence; different rows can cancel out.
- `SUM` is a partial signal and may overflow for some numeric types; the collector currently fails closed if the database query fails.
- SQL type strings are not normalized; metadata completeness, permissions, snapshot consistency, and certificate validation remain unverified.
- Never label this output 'migration certified' or 'independently validated'.
- Before a paid pilot: independent database permissions tests, schema completeness checks, resource limits, signed evidence/provenance and customer authorization.
