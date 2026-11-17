"""Strict offline keyed-row reconciliation over caller-supplied sanitized JSON.

This is not a SQL collector and does not prove database completeness.
Never include raw row values or raw keys in findings.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

MAX_ROWS = 10_000
MAX_COLUMNS = 100
MAX_CELL_CHARS = 16_384
MAX_KEY_CHARS = 128


class RowEvidenceError(ValueError):
    """Input is incomplete, ambiguous, oversized or unsupported."""


def _scalar(value: Any) -> bool:
    # Floats are rejected: JSON decimal values must be supplied as canonical
    # strings so they cannot be rounded before reaching this comparator.
    return value is None or type(value) in (str, int, bool)


def _canon(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _validate(document: Any) -> tuple[str, tuple[str, ...], tuple[str, ...], dict[tuple[str, ...], dict[str, Any]]]:
    if not isinstance(document, dict) or set(document) != {"table", "key_columns", "compare_columns", "rows"}:
        raise RowEvidenceError("Evidence must provide table, key_columns, compare_columns and rows")
    table = document["table"]
    if not isinstance(table, str) or not table.strip() or len(table) > 256:
        raise RowEvidenceError("Invalid table identity")
    keys, columns, rows = (document[name] for name in ("key_columns", "compare_columns", "rows"))
    if (not isinstance(keys, list) or not keys or not isinstance(columns, list)
            or not columns or len(keys) + len(columns) > MAX_COLUMNS):
        raise RowEvidenceError("Invalid key/compare column selection")
    expected = keys + columns
    if (any(not isinstance(c, str) or not c or len(c) > MAX_KEY_CHARS for c in expected)
            or len(set(expected)) != len(expected)):
        raise RowEvidenceError("Duplicate, oversized or invalid column names")
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise RowEvidenceError("Row budget exceeded or invalid rows")
    index: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(expected):
            raise RowEvidenceError("Row is missing required columns or has unexpected columns")
        if any(not _scalar(value) or
               (type(value) is str and len(value) > MAX_CELL_CHARS) for value in row.values()):
            raise RowEvidenceError("Unsupported or oversized value; use canonical decimal strings")
        key_values = [row[name] for name in keys]
        if any(value is None for value in key_values):
            raise RowEvidenceError("Null keys are not supported")
        encoded = tuple(_canon(value) for value in key_values)
        if encoded in index:
            raise RowEvidenceError("Duplicate key; deterministic matching impossible")
        index[encoded] = row
    return table, tuple(keys), tuple(columns), index


def reconcile_rows(source: Any, target: Any) -> dict[str, Any]:
    """Compare only explicitly selected and supplied rows; never expose values.

    Schema/key selection mismatch raises RowEvidenceError (not an empty PASS).
    For privacy, the output contains counts, not row-level identifiers.
    """
    s_table, s_keys, s_columns, s_rows = _validate(source)
    t_table, t_keys, t_columns, t_rows = _validate(target)
    if (s_table, s_keys, s_columns) != (t_table, t_keys, t_columns):
        raise RowEvidenceError("Source and target comparison scope differs")
    only_source = s_rows.keys() - t_rows.keys()
    only_target = t_rows.keys() - s_rows.keys()
    changed = sum(
        1 for key in s_rows.keys() & t_rows.keys()
        if any(_canon(s_rows[key][col]) != _canon(t_rows[key][col])
               for col in s_columns)
    )
    differences = len(only_source) + len(only_target) + changed
    return {
        "engine": "migrationproof.offline-rows.v1",
        "table": s_table,
        "key_columns": list(s_keys),
        "compare_columns": list(s_columns),
        "source_rows_supplied": len(s_rows),
        "target_rows_supplied": len(t_rows),
        "missing_target_keys": len(only_source),
        "extra_target_keys": len(only_target),
        "changed_matching_keys": changed,
        "status": "DIFFERENCES_FOUND" if differences else "SUPPLIED_ROWS_MATCH",
        "scope": ("Only supplied sanitized rows and selected columns were compared. "
                  "Completeness, point-in-time consistency, and SQL Server correctness are unverified."),
    }
