"""Offline evidence manifests: integrity checks, not signatures or authenticity claims.

All evidence file paths are relative to an explicitly supplied directory.
Symlinks, missing files, traversal and changed content are rejected.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

FORMAT_VERSION = "migrationproof.evidence.v1"
READ_CHUNK_BYTES = 1024 * 1024
MAX_FILES = 1000
MAX_FILE_BYTES = 128 * 1024 * 1024


class EvidenceError(ValueError):
    """A bundle is missing, changed, unsafe or malformed."""


def _safe_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise EvidenceError("Evidence path must be a nonempty relative POSIX path")
    parsed = PurePosixPath(relative)
    if (parsed.is_absolute() or relative.startswith("\\") or "\\" in relative
            or ":" in relative or any(part in {"", ".", ".."} for part in parsed.parts)
            or parsed.as_posix() != relative):
        raise EvidenceError("Unsafe evidence path")
    current = root
    for component in parsed.parts:
        current = current / component
        if current.is_symlink():
            raise EvidenceError("Evidence symlinks are not permitted")
    if not current.is_file():
        raise EvidenceError("Evidence file missing or not regular")
    return current


def _digest(path: Path) -> tuple[str, int]:
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise EvidenceError("Evidence exceeds maximum file size")
    sha = hashlib.sha256()
    observed = 0
    with path.open("rb") as handle:
        while chunk := handle.read(READ_CHUNK_BYTES):
            observed += len(chunk)
            if observed > MAX_FILE_BYTES:
                raise EvidenceError("Evidence file grew beyond maximum size")
            sha.update(chunk)
    if observed != size or path.stat().st_size != size:
        raise EvidenceError("Evidence changed during hashing")
    return sha.hexdigest(), observed


def build_manifest(root: Path, names: list[str]) -> dict[str, Any]:
    """Generate a deterministic manifest over explicitly selected evidence files."""
    root = Path(root).resolve(strict=True)
    if not root.is_dir() or not names or len(names) > MAX_FILES or len(names) != len(set(names)):
        raise EvidenceError("Invalid evidence root or file selection")
    result = []
    for relative in sorted(names):
        file_path = _safe_file(root, relative)
        sha, size = _digest(file_path)
        result.append({"path": relative, "sha256": sha, "size_bytes": size})
    return {
        "format": FORMAT_VERSION,
        "integrity_only": True,
        "scope": "File-byte integrity, not provenance, database truth, completeness or authenticity",
        "files": result,
    }


def verify_manifest(root: Path, manifest: dict[str, Any]) -> None:
    """Raise EvidenceError unless the manifest matches every named file."""
    if not isinstance(manifest, dict) or set(manifest) != {"format", "integrity_only", "scope", "files"}:
        raise EvidenceError("Unsupported evidence manifest schema")
    if manifest["format"] != FORMAT_VERSION or manifest["integrity_only"] is not True:
        raise EvidenceError("Unsupported evidence manifest format")
    files = manifest["files"]
    if not isinstance(files, list) or not files or len(files) > MAX_FILES:
        raise EvidenceError("Invalid evidence file list")
    names = []
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size_bytes"}:
            raise EvidenceError("Invalid evidence entry")
        relative = entry["path"]
        sha = entry["sha256"]
        size = entry["size_bytes"]
        if not isinstance(relative, str) or not isinstance(sha, str) or len(sha) != 64:
            raise EvidenceError("Invalid evidence path or SHA-256")
        if any(c not in "0123456789abcdef" for c in sha):
            raise EvidenceError("Invalid SHA-256 encoding")
        if type(size) is not int or size < 0 or size > MAX_FILE_BYTES:
            raise EvidenceError("Invalid evidence size")
        names.append(relative)
    if names != sorted(set(names)):
        raise EvidenceError("Evidence entries must be unique and sorted")
    actual = build_manifest(root, names)
    if actual["files"] != files:
        raise EvidenceError("Evidence contents do not match manifest")


def dumps_manifest(manifest: dict[str, Any]) -> str:
    """Canonical, deterministic JSON for review and external signing."""
    return json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
