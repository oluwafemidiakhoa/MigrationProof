# Offline keyed-row reconciliation (experimental)

MigrationProof can compare **only explicitly supplied sanitized rows** using selected key columns and comparison columns. This is separate from the SQL Server collector: no database access or automated extraction is implemented.

## Input

Both JSON files require the same `table`, `key_columns`, and `compare_columns`:

```json
{
  "table": "dbo.Orders",
  "key_columns": ["OrderID"],
  "compare_columns": ["Amount", "Status"],
  "rows": [
    {"OrderID": 1, "Amount": "10.00", "Status": "paid"},
    {"OrderID": 2, "Amount": "20.00", "Status": "paid"}
  ]
}
```

Amounts must be passed as canonical strings rather than JSON floating-point numbers. The comparator uses exact, type-sensitive equality; it **does not** normalize decimal formatting, collations, dates, timezone, Unicode or SQL NULL semantics.

## CLI

```bash
python -m migrationproof.rows_cli source_rows.json target_rows.json --output row_report.json
```

Exit 0: supplied rows match. Exit 1: differences found. Exit 2: malformed, ambiguous, inaccessible or incomplete input. Existing reports are not overwritten.

## Scope and safety

- Each input is limited to 10,000 rows and 100 total selected columns.
- Duplicate or NULL keys, unexpected columns, nested values, floats and oversized text fail closed.
- The report contains counts only: matching keys whose selected values changed, keys absent from target and keys added in target. No raw row values or row identifiers are written to the report.
- Input row contents and keys must already be **sanitized**, because source files still contain raw provided values.
- Equal row counts and equal numeric sums do not prove equality; keyed comparison catches changed pairs in the tested subset.
- Zero differences proves only equality of **supplied** rows under selected columns, not completeness of database collection or a transactionally consistent migration.
- No customer data or production databases should be used without a separate approved collection design, legal authority, permissions, minimization and resource controls.

## Follow-on gates

Signed evidence manifests; key/column canonicalization contract; privacy-safe selective hashing; explicit completeness and coverage manifest; non-production SQL Server integration; reproducible point-in-time collection; independent verification.
