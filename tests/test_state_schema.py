from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumen_lab.state_schema import (
    MANAGED_FILES,
    MANIFEST_NAME,
    current_manifest,
    load_manifest,
    migrate_legacy_manifest,
    migration_plan,
    validate_state_schema,
)


def _write_managed_files(root: Path) -> None:
    state = root / "state"
    state.mkdir(parents=True)
    for name in MANAGED_FILES:
        (state / name).write_text("{}\n", encoding="utf-8")


def test_current_manifest_is_deterministic() -> None:
    first = current_manifest().to_dict()
    second = current_manifest().to_dict()
    assert first == second
    assert list(first["files"]) == sorted(first["files"])


def test_validate_state_schema_accepts_current_manifest(tmp_path: Path) -> None:
    _write_managed_files(tmp_path)
    manifest = current_manifest()
    path = tmp_path / "state" / MANIFEST_NAME
    path.write_text(json.dumps(manifest.to_dict()), encoding="utf-8")

    loaded = validate_state_schema(tmp_path)

    assert loaded == manifest


def test_load_manifest_rejects_future_manifest_version(tmp_path: Path) -> None:
    path = tmp_path / MANIFEST_NAME
    path.write_text(
        json.dumps({"manifest_version": 2, "files": MANAGED_FILES}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsupported manifest_version"):
        load_manifest(path)


def test_load_manifest_rejects_unknown_managed_file(tmp_path: Path) -> None:
    files = dict(MANAGED_FILES)
    files["mystery.json"] = 1
    path = tmp_path / MANIFEST_NAME
    path.write_text(json.dumps({"manifest_version": 1, "files": files}), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown files"):
        load_manifest(path)


def test_validate_state_schema_rejects_missing_managed_file(tmp_path: Path) -> None:
    _write_managed_files(tmp_path)
    (tmp_path / "state" / "profile.json").unlink()
    path = tmp_path / "state" / MANIFEST_NAME
    path.write_text(json.dumps(current_manifest().to_dict()), encoding="utf-8")
    with pytest.raises(ValueError, match="managed state file is missing"):
        validate_state_schema(tmp_path)


def test_migration_plan_is_read_only_for_legacy_state(tmp_path: Path) -> None:
    _write_managed_files(tmp_path)
    before = sorted((tmp_path / "state").iterdir())

    plan = migration_plan(tmp_path)

    after = sorted((tmp_path / "state").iterdir())
    assert before == after
    assert plan["status"] == "legacy-unversioned"
    assert plan["writes_payload_files"] is False


def test_migrate_legacy_manifest_creates_only_manifest(tmp_path: Path) -> None:
    _write_managed_files(tmp_path)
    payloads = {
        name: (tmp_path / "state" / name).read_bytes()
        for name in MANAGED_FILES
    }

    manifest = migrate_legacy_manifest(tmp_path)

    assert manifest == current_manifest()
    assert (tmp_path / "state" / MANIFEST_NAME).is_file()
    for name, content in payloads.items():
        assert (tmp_path / "state" / name).read_bytes() == content
    assert migration_plan(tmp_path)["status"] == "current"


def test_real_repository_schema_manifest_is_healthy() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = validate_state_schema(root)
    assert manifest == current_manifest()
