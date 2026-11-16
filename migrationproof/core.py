"""Compare sanitized migration snapshots without connecting to databases."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TableSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    columns: dict[str, str]
    row_count: int = Field(ge=0)
    aggregates: dict[str, float | int | str | None] = Field(default_factory=dict)


class DatabaseSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    database: str = Field(min_length=1)
    tables: dict[str, TableSnapshot]


def canonical_digest(snapshot: DatabaseSnapshot) -> str:
    payload = json.dumps(snapshot.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def reconcile(source: DatabaseSnapshot, target: DatabaseSnapshot) -> dict[str, Any]:
    """Return deterministic findings. Aggregate equality is exact, never approximate."""
    findings: list[dict[str, str]] = []
    def add(code: str, table: str, detail: str) -> None:
        findings.append({"code": code, "table": table, "detail": detail})

    for table in sorted(set(source.tables) | set(target.tables)):
        left = source.tables.get(table)
        right = target.tables.get(table)
        if left is None:
            add("EXTRA_TARGET_TABLE", table, "Table exists only in target")
            continue
        if right is None:
            add("MISSING_TARGET_TABLE", table, "Table exists only in source")
            continue
        for column in sorted(set(left.columns) | set(right.columns)):
            if column not in right.columns:
                add("MISSING_TARGET_COLUMN", table, column)
            elif column not in left.columns:
                add("EXTRA_TARGET_COLUMN", table, column)
            elif left.columns[column] != right.columns[column]:
                add("COLUMN_TYPE_MISMATCH", table, column)
        if left.row_count != right.row_count:
            add("ROW_COUNT_MISMATCH", table, f"source={left.row_count}, target={right.row_count}")
        for metric in sorted(set(left.aggregates) | set(right.aggregates)):
            if metric not in right.aggregates or metric not in left.aggregates:
                add("AGGREGATE_MISSING", table, metric)
            elif type(left.aggregates[metric]) is not type(right.aggregates[metric]) or left.aggregates[metric] != right.aggregates[metric]:
                add("AGGREGATE_MISMATCH", table, metric)
    return {
        "engine_version": "0.1.0",
        "source_database": source.database,
        "target_database": target.database,
        "source_sha256": canonical_digest(source),
        "target_sha256": canonical_digest(target),
        "status": "DIFFERENCES_FOUND" if findings else "CHECKS_PASSED",
        "scope": "Only supplied table schemas, row counts and aggregate metrics were compared; passing is not proof of full migration equivalence.",
        "findings": findings,
    }
