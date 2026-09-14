from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "apps" / "desktop"


def desktop_versions() -> dict[str, str]:
    package = json.loads((DESKTOP / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads(
        (DESKTOP / "package-lock.json").read_text(encoding="utf-8")
    )
    tauri = json.loads(
        (DESKTOP / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8")
    )
    with (DESKTOP / "src-tauri" / "Cargo.toml").open("rb") as handle:
        cargo = tomllib.load(handle)

    return {
        "package.json": package["version"],
        "package-lock.json": package_lock["version"],
        "package-lock.json root package": package_lock["packages"][""]["version"],
        "tauri.conf.json": tauri["version"],
        "Cargo.toml": cargo["package"]["version"],
    }


def test_desktop_release_manifests_share_one_version() -> None:
    versions = desktop_versions()
    assert len(set(versions.values())) == 1, versions


def test_readme_installer_name_matches_desktop_version() -> None:
    version = next(iter(desktop_versions().values()))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert f"Lumen_{version}_x64-setup.exe" in readme


def test_release_workflow_validates_manifests_and_tag_provenance() -> None:
    workflow = (ROOT / ".github/workflows/windows-installer.yml").read_text(encoding="utf-8")
    assert 'python packaging/check_release.py --ref "$env:RELEASE_REF"' in workflow
    assert 'python3 packaging/check_release.py --ref "$GITHUB_REF" --sha "$GITHUB_SHA"' in workflow
