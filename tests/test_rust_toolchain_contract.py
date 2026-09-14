from __future__ import annotations

import tomllib
from pathlib import Path

TOOLCHAIN_PATH = Path("rust-toolchain.toml")
DESKTOP_CI_PATH = Path(".github/workflows/desktop-ci.yml")
WINDOWS_INSTALLER_PATH = Path(".github/workflows/windows-installer.yml")
EXPECTED_RUST_VERSION = "1.98.1"


def test_rust_toolchain_is_pinned_to_an_exact_version() -> None:
    toolchain = tomllib.loads(TOOLCHAIN_PATH.read_text(encoding="utf-8"))["toolchain"]

    assert toolchain["channel"] == EXPECTED_RUST_VERSION
    assert toolchain["profile"] == "minimal"


def test_desktop_workflows_follow_the_repository_toolchain_pin() -> None:
    for workflow_path in (DESKTOP_CI_PATH, WINDOWS_INSTALLER_PATH):
        workflow = workflow_path.read_text(encoding="utf-8")

        assert '"rust-toolchain.toml"' in workflow
        assert "rustup update stable" not in workflow
        assert "rustup default stable" not in workflow
