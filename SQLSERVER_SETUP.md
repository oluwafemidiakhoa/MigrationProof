# MigrationProof SQL Server collector — experimental scoped lab use

This collector is **not approved for production or unrestricted customer databases**. It connects only to the explicitly named database and explicitly listed tables, and it refuses any table containing more than the configured row budget. The collector does not perform DML or DDL, but reads can still consume resources or take locks. It does **not** prove a transactionally consistent snapshot or complete migration equivalence.

## Required checks

- Use an approved disposable non-production SQL Server database and separately created read-only login.
- Require verified TLS: ODBC Driver 18 with `Encrypt=yes;TrustServerCertificate=no`. Never weaken validation to make a connection succeed.
- Supply `--expected-database`, one or more `--table schema.table` values and an independently reviewed `--expected-columns` JSON inventory. Missing/hidden/extra columns in an allowed table are errors, not success. Inventory must NOT be generated using the same low-permission collector.
- Set a conservative `--max-rows-per-table` (default 10000) and `--timeout` (default 15 seconds). Table counts are bounded by an N+1 TOP subquery; opt-in SUM applies only after counts pass.
- Treat result as **scope-limited**, not a guarantee that there are no invisible tables or rows excluded by row-level security.
- `SUM` can be expensive even on allowed tables, may overflow, and is inappropriate as sole evidence of row equivalence.
- Report completeness must be independently reviewed. Snapshot collection timestamps, isolation levels, source/target coherence, and signed evidence are future gates.
- Never commit captured database metadata or customer evidence to the repository.

## Approved column inventory\n\nThe operator creates a separate, manually reviewed `approved_lab_columns.json` by an authorized higher-visibility inventory process. Example only, adjust to actual lab schema:\n\n```json\n{\n  "dbo.Orders": ["OrderID", "Amount"]\n}\n```\n\nThis validates visible column names against supplied expectations; it does **not** establish that the inventory itself is exhaustive, that row-level security is absent, or that source/target snapshots were transactionally consistent.\n\n## Windows Command Prompt example

```bat
python -m pip install pyodbc
set "MIGRATIONPROOF_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=LAB_SERVER;DATABASE=MigrationProofSourceLab;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=no;"
python -m migrationproof.sqlserver_cli --output source_lab.json --expected-database MigrationProofSourceLab --table dbo.Orders --expected-columns approved_lab_columns.json --max-rows-per-table 1000 --sum-column Amount
```

Repeat with an independently collected target snapshot and its own explicit expected database. Then compare:

```bat
python -m migrationproof.cli source_lab.json target_lab.json --output lab_report.json
python -m migrationproof.report_cli lab_report.json --output lab_report.html
```

The compare CLI intentionally returns exit code 1 when differences are found. A zero exit means only that the **implemented checks over supplied evidence** matched, not that migration was independently verified.

## Remaining release blockers

Real SQL Server integration tests on an approved disposable instance; permissions-visibility tests; consistent snapshot isolation strategy; performance measurement; discovery completeness; typed numerical comparison; row-level reconciliation; signed provenance; redaction and retention policies; documented operator approval and customer boundaries.
