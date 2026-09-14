from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .state_io import write_json_atomic

MANIFEST_VERSION = 1
MANIFEST_NAME = "schema_versions.json"
MANAGED_FILES: dict[str, int] = {
    "backlog.json": 1,
    "calibration_baseline.json": 1,
    "candidates.json": 1,
    "capabilities.json": 1,
    "missions.json": 1,
    "outcomes.json": 1,
    "profile.json": 1,
    "provenance.json": 1,
    "work_sessions.json": 1,
}


@dataclass(frozen=True, slots=True)
class SchemaManifest:
    manifest_version: int
    files: dict[str, int]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> SchemaManifest:
        expected = {"manifest_version", "files"}
        unknown = set(raw) - expected
        missing = expected - set(raw)
        if unknown:
            raise ValueError(f"unknown schema manifest fields: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing schema manifest fields: {', '.join(sorted(missing))}")

        manifest = cls(manifest_version=raw["manifest_version"], files=raw["files"])
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if isinstance(self.manifest_version, bool) or not isinstance(self.manifest_version, int):
            raise ValueError("manifest_version must be an integer")
        if self.manifest_version != MANIFEST_VERSION:
            message = (
                f"unsupported manifest_version {self.manifest_version}; "
                f"supported: {MANIFEST_VERSION}"
            )
            raise ValueError(message)
        if not isinstance(self.files, dict):
            raise ValueError("schema manifest files must be a JSON object")

        expected_names = set(MANAGED_FILES)
        actual_names = set(self.files)
        missing = sorted(expected_names - actual_names)
        unknown = sorted(actual_names - expected_names)
        if missing:
            raise ValueError(f"schema manifest missing managed files: {', '.join(missing)}")
        if unknown:
            raise ValueError(f"schema manifest contains unknown files: {', '.join(unknown)}")

        for name, version in sorted(self.files.items()):
            if isinstance(version, bool) or not isinstance(version, int) or version < 1:
                raise ValueError(f"schema version for {name} must be a positive integer")
            supported = MANAGED_FILES[name]
            if version != supported:
                raise ValueError(
                    f"unsupported schema version for {name}: {version}; supported: {supported}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "files": dict(sorted(self.files.items())),
        }


def current_manifest() -> SchemaManifest:
    return SchemaManifest(MANIFEST_VERSION, dict(MANAGED_FILES))


def load_manifest(path: Path) -> SchemaManifest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("schema manifest must contain a JSON object")
    return SchemaManifest.from_dict(raw)


def validate_state_schema(root: Path) -> SchemaManifest:
    state_dir = root / "state"
    manifest = load_manifest(state_dir / MANIFEST_NAME)
    for name in sorted(manifest.files):
        path = state_dir / name
        if not path.is_file():
            raise ValueError(f"managed state file is missing: state/{name}")
    return manifest


def migration_plan(root: Path) -> dict[str, Any]:
    path = root / "state" / MANIFEST_NAME
    if not path.exists():
        return {
            "status": "legacy-unversioned",
            "changes": [f"create state/{MANIFEST_NAME} at manifest version {MANIFEST_VERSION}"],
            "writes_payload_files": False,
        }

    manifest = validate_state_schema(root)
    return {
        "status": "current",
        "manifest_version": manifest.manifest_version,
        "changes": [],
        "writes_payload_files": False,
    }


def migrate_legacy_manifest(root: Path) -> SchemaManifest:
    state_dir = root / "state"
    path = state_dir / MANIFEST_NAME
    if path.exists():
        return validate_state_schema(root)

    missing = [name for name in sorted(MANAGED_FILES) if not (state_dir / name).is_file()]
    if missing:
        raise ValueError(
            "cannot migrate legacy state; managed files are missing: " + ", ".join(missing)
        )

    manifest = current_manifest()
    write_json_atomic(path, manifest.to_dict())
    return manifest
