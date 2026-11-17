# MigrationProof v0.1

This is an **offline development prototype**, not a production assurance certificate.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
python -m pip install -e ".[dev]"
python -m pytest -q
python -m migrationproof.cli examples/source.json examples/target.json --output report.json
```

The example intentionally differs, so the CLI exits with status 1. A status of 0 means only that the implemented checks passed.

## Safety and scope

- No database credentials, network connections, SQL execution, or automatic remediation.
- Snapshot JSON is untrusted input; validate locally and avoid uploading sensitive datasets.
- SHA-256 proves snapshot bytes are stable under canonical serialization, not that the source database is accurate.
- Column type strings are compared literally, without SQL type normalization.
- Counts and aggregates are provided by the caller, not independently verified.
- Production readiness, SQL Server collection, SSIS analysis, authorization, and signed reports are **not implemented**.
