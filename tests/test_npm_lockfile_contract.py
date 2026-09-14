from __future__ import annotations

import json
from pathlib import Path

DESKTOP_PACKAGE_PATH = Path("apps/desktop/package.json")
DESKTOP_LOCK_PATH = Path("apps/desktop/package-lock.json")
DESKTOP_CI_PATH = Path(".github/workflows/desktop-ci.yml")
WINDOWS_INSTALLER_PATH = Path(".github/workflows/windows-installer.yml")


def test_desktop_lockfile_matches_package_metadata_and_top_level_dependencies() -> None:
    package = json.loads(DESKTOP_PACKAGE_PATH.read_text(encoding="utf-8"))
    lockfile = json.loads(DESKTOP_LOCK_PATH.read_text(encoding="utf-8"))
    root_package = lockfile["packages"][""]

    assert lockfile["lockfileVersion"] == 3
    assert lockfile["name"] == package["name"]
    assert lockfile["version"] == package["version"]
    assert root_package["name"] == package["name"]
    assert root_package["version"] == package["version"]
    assert root_package["dependencies"] == package["dependencies"]
    assert root_package["devDependencies"] == package["devDependencies"]


def test_desktop_workflows_require_clean_lockfile_installs() -> None:
    for workflow_path in (DESKTOP_CI_PATH, WINDOWS_INSTALLER_PATH):
        workflow = workflow_path.read_text(encoding="utf-8")

        assert "npm ci" in workflow
        assert "npm install" not in workflow
        assert "apps/desktop/package-lock.json" in workflow
