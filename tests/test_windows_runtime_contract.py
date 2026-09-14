import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_TAURI_CONFIG = REPO_ROOT / "apps" / "desktop" / "src-tauri" / "tauri.windows.conf.json"
WINDOWS_HOST = REPO_ROOT / "apps" / "desktop" / "src-tauri" / "src" / "main.rs"
DESKTOP_BRIDGE = REPO_ROOT / "apps" / "desktop" / "src" / "lib" / "lumen.ts"
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


def test_tauri_host_keeps_blocking_engine_work_off_async_runtime_and_times_out() -> None:
    source = WINDOWS_HOST.read_text(encoding="utf-8")

    assert "ENGINE_TIMEOUT_SECONDS" in source
    assert "child.try_wait()" in source
    assert "child.kill()" in source
    assert "ENGINE_REQUEST_LOCK" in source
    assert "ENGINE_REQUEST_LOCK.lock().await" in source
    assert "spawn_writer(stdin, request.into_bytes())" in source
    assert "tauri::async_runtime::spawn_blocking" in source


def test_installer_stages_engine_at_configured_source_path() -> None:
    workflow = INSTALLER_WORKFLOW.read_text(encoding="utf-8")

    assert "apps\\desktop\\src-tauri\\resources\\lumen-engine.exe" in workflow
    assert "Copy-Item dist\\lumen-engine.exe" in workflow


def test_installer_smoke_tests_engine_from_installed_nsis_bundle() -> None:
    workflow = INSTALLER_WORKFLOW.read_text(encoding="utf-8")

    assert "Install and smoke test NSIS bundle" in workflow
    assert "Start-Process -FilePath $installer.FullName" in workflow
    assert "-ArgumentList @('/S', \"/D=$installDir\")" in workflow
    assert "Get-ChildItem -Path $installDir -Filter lumen-engine.exe -Recurse" in workflow
    assert '"user_id":"installed-smoke"' in workflow
    assert "Get-ChildItem -Path $installDir -Filter lumen-desktop.exe -Recurse" in workflow
    assert "Start-Process -FilePath $desktop.FullName" in workflow
    assert "Installed Lumen GUI exited during startup" in workflow


def test_completed_step_refreshes_dashboard_in_one_engine_request() -> None:
    source = DESKTOP_BRIDGE.read_text(encoding="utf-8")
    function = source[source.index("export function completeStep"):]
    function = function[:function.index("\n}")]

    assert function.count('request<Dashboard>("complete_step"') == 1
    assert 'request<Dashboard>("dashboard"' not in function
