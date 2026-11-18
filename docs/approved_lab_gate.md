# Opt-in SQL Server lab integration gate

**Status: NOT_TESTED until an operator runs it on a separately approved disposable SQL Server lab.** Passing normal GitHub CI only proves offline gate logic and unit tests.

## Scope, approvals and safety

- Exact approved lab host recorded independently by the operator (not merely a host name that looks like 'lab')
- Two databases named `MigrationProofSourceLab` and `MigrationProofTargetLab` with the checked-in synthetic table `dbo.Orders`
- **Never** use a production/company SQL Server, real customer rows, or shared integration host without explicit administrator approval and cost/risk review
- Lab database creation is a separate, manual action in `docs/lab_source_target_demo.sql`; script refuses to create if either database already exists
- No database creation, modification or cleanup is performed by this Python gate
- Exact six-option ODBC connection profile: `DRIVER={ODBC Driver 18 for SQL Server};SERVER=<approved host>;DATABASE=<approved lab database>;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=no`. Any other, duplicated, omitted, or conflicting option fails closed before connecting. Validating these strings is not a substitute for verifying the actual certificate chain and server identity on a real lab host.
- A narrowly scoped read-only database principal; operating-system environment variables hold credentials/connection details and are not committed
- Collector bounds: one table, at most 10 rows, 10-second query timeout
- **No automatic GitHub Actions live SQL job** or hidden connection fallback

## Operator procedure (Windows Command Prompt)

After obtaining documented approval for a disposable non-production SQL Server, review and manually execute the synthetic setup script on that isolated environment. Configure the driver and certificate trust properly.

```bat
set "MIGRATIONPROOF_LAB_APPROVAL=I_APPROVE_DISPOSABLE_SQLSERVER_LAB_READS"
set "MIGRATIONPROOF_APPROVED_LAB_SERVER=YOUR_EXACT_APPROVED_LAB_HOST"
set "MIGRATIONPROOF_LAB_SOURCE_CONNECTION=DRIVER={ODBC Driver 18 for SQL Server};SERVER=YOUR_EXACT_APPROVED_LAB_HOST;DATABASE=MigrationProofSourceLab;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=no;"
set "MIGRATIONPROOF_LAB_TARGET_CONNECTION=DRIVER={ODBC Driver 18 for SQL Server};SERVER=YOUR_EXACT_APPROVED_LAB_HOST;DATABASE=MigrationProofTargetLab;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=no;"
set "MIGRATIONPROOF_LAB_RECEIPT=C:\\local-private-evidence\\migrationproof_lab_receipt.json"
python -m scripts.run_sqlserver_lab_gate
```

Receipt must be a new path, on an operator-controlled private drive. Existing files cannot be overwritten. The gate prints no driver exception contents or connection secrets. Exit 0 indicates a successful **synthetic lab test only**; exit 2 means NOT_TESTED/INCOMPLETE.

## Required observations and remaining gates

Expected synthetic source: row count 3; `sum:Amount=150.00`. Expected target: row count 3; `sum:Amount=1124.00`. Result must show a detected aggregate mismatch. Any variation aborts.

After the test, a qualified operator must independently verify: actual SQL Server identity, TLS certificate chain, login least privileges and object visibility, RLS absence/visibility, query resource use and query timeout, column inventory source, snapshot transaction semantics, and evidence provenance. This test **does not** demonstrate production safety or source-target point-in-time consistency.

Never claim that an operator-supplied approval string or output receipt independently establishes permission; they are procedural assertions requiring separate approval evidence.

## Runtime SQL identity and encryption checks

The lab gate now requires `SERVERPROPERTY('ServerName')` to match `MIGRATIONPROOF_APPROVED_LAB_SERVER` *exactly*, and reads `sys.dm_exec_connections.encrypt_option` for its session. The approved value therefore must be the SQL Server instance name reported by `SERVERPROPERTY('ServerName')`, not an unverified DNS alias; if the ODBC endpoint uses an alias, the operator must verify that it resolves only to the authorized isolated instance. When the DMV is inaccessible to the least-privileged test account, the gate fails closed and the permission model requires review. Do not grant excessive privileges merely to make the test pass.

`encrypt_option=TRUE` reports encrypted transport but does NOT independently prove the server certificate-chain or trust anchor is valid. ODBC Driver 18 certificate validation must still be tested and reviewed on the live lab host. These checks do not establish that the host was authorized or that another similarly named host is isolated. No real SQL Server test has been run by this change.
