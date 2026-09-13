import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_TAURI_CONFIG = REPO_ROOT / "apps" / "desktop" / "src-tauri" / "tauri.windows.conf.json"
WINDOWS_HOST = REPO_ROOT / "apps" / "desktop" / "src-tauri" / "src" / "main.rs"
INSTALLER_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "windows-installer.yml"


def test_windows_bundle_maps_engine_to_resource_root() -> None:
    config = json.loads(WINDOWS_TAURI_CONFIG.read_text(encoding="utf-8"))

    resources = config["bundle"]["resources"]
    assert resources == {"resources/lumen-engine.exe": "lumen-engine.exe"}


def test_tauri_host_resolves_engine_from_resource_root() -> None:
    source = WINDOWS_HOST.read_text(encoding="utf-8")

    assert '"lumen-engine.exe"' in source
    assert "BaseDirectory::Resource" in source
    assert "app.path().resolve(relative, BaseDirectory::Resource)" in source


def test_installer_stages_engine_at_configured_source_path() -> None:
    workflow = INSTALLER_WORKFLOW.read_text(encoding="utf-8")

    assert "apps\\desktop\\src-tauri\\resources\\lumen-engine.exe" in workflow
    assert "Copy-Item dist\\lumen-engine.exe" in workflow
