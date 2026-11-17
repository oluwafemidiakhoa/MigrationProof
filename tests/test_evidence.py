import json

import pytest

from migrationproof.evidence import (
    EvidenceError,
    FORMAT_VERSION,
    build_manifest,
    dumps_manifest,
    verify_manifest,
)


def test_manifest_is_deterministic_and_verifies(tmp_path):
    (tmp_path / "a.json").write_text('{"a":1}', encoding="utf-8")
    (tmp_path / "b.txt").write_text("hello", encoding="utf-8")
    first = build_manifest(tmp_path, ["b.txt", "a.json"])
    second = build_manifest(tmp_path, ["a.json", "b.txt"])
    assert first == second
    assert first["format"] == FORMAT_VERSION
    assert first["integrity_only"] is True
    assert dumps_manifest(first) == dumps_manifest(second)
    verify_manifest(tmp_path, json.loads(dumps_manifest(first)))


def test_tamper_detected(tmp_path):
    file_path = tmp_path / "report.json"
    file_path.write_text("original", encoding="utf-8")
    manifest = build_manifest(tmp_path, ["report.json"])
    file_path.write_text("modified", encoding="utf-8")
    with pytest.raises(EvidenceError, match="do not match"):
        verify_manifest(tmp_path, manifest)


def test_deleted_file_fails(tmp_path):
    file_path = tmp_path / "evidence.json"
    file_path.write_text("receipt", encoding="utf-8")
    manifest = build_manifest(tmp_path, ["evidence.json"])
    file_path.unlink()
    with pytest.raises(EvidenceError, match="missing"):
        verify_manifest(tmp_path, manifest)


@pytest.mark.parametrize("name", [
    "../outside.txt", "/tmp/outside.txt", "dir/../evidence.json",
    "C:/Windows/win.ini", r"sub\\evidence.json", "",
])
def test_unsafe_paths_rejected(tmp_path, name):
    (tmp_path / "evidence.json").write_text("receipt", encoding="utf-8")
    with pytest.raises(EvidenceError):
        build_manifest(tmp_path, [name])


def test_symlink_rejected(tmp_path):
    target = tmp_path / "actual.txt"
    target.write_text("receipt", encoding="utf-8")
    try:
        (tmp_path / "shortcut.txt").symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable")
    with pytest.raises(EvidenceError, match="symlink"):
        build_manifest(tmp_path, ["shortcut.txt"])


def test_malformed_manifest_fails_closed(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    manifest = build_manifest(tmp_path, ["a.txt"])
    for changed in (
        {**manifest, "format": "unsupported"},
        {**manifest, "integrity_only": False},
        {**manifest, "files": [{**manifest["files"][0], "sha256": "0" * 64}]},
        {**manifest, "files": [{**manifest["files"][0], "size_bytes": True}]},
        {**manifest, "files": manifest["files"] * 2},
    ):
        with pytest.raises(EvidenceError):
            verify_manifest(tmp_path, changed)


def test_reject_duplicate_selection(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    with pytest.raises(EvidenceError):
        build_manifest(tmp_path, ["a.txt", "a.txt"])
