# MigrationProof v0.2: SQL Server test collector

The collector is experimental. It reads catalog metadata and executes COUNT_BIG(*) on every visible user table. It does not write SQL data. COUNT_BIG can be expensive, block, or produce inconsistent cross-table results during concurrent writes.

Use **only an approved disposable test database**. Do not use master or organizational business databases.

## Windows Command Prompt

```bat
python -m pip install pyodbc
set "MIGRATIONPROOF_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=FXL-WSV-SQL;DATABASE=MigrationProofTest;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;"
python -m migrationproof.sqlserver_cli --output test_snapshot.json --max-tables 10
```

The TrustServerCertificate setting is a **temporary diagnostic exception** for this approved test database only. Use certificate verification for real customer assessments.

To render the existing offline report:

```bat
python -m migrationproof.report_cli report.json --output report.html
start report.html
```

Never commit connection strings, credentials, or customer snapshots. For customer use, implement strict allowlists, scoped accounts, certificate validation, query cost bounds, and integration tests first.
