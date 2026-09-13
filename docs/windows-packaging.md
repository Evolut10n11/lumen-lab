# Windows packaging contract

The Windows desktop build has two executables with different jobs:

- the Tauri host (`Lumen.exe`) owns the desktop window and IPC boundary;
- the standalone Python engine (`lumen-engine.exe`) serves the local JSON bridge used by the host.

The installer build creates `lumen-engine.exe` with PyInstaller, smoke-tests it directly, then stages it at `apps/desktop/src-tauri/resources/lumen-engine.exe` before Tauri builds the NSIS installer.

`apps/desktop/src-tauri/tauri.windows.conf.json` maps that staged source to `lumen-engine.exe` at the Tauri resource root. The Rust host resolves `lumen-engine.exe` relative to `BaseDirectory::Resource` in release builds. Development builds may fall back to `python -m lumen_lab.desktop_bridge`, but release builds must fail with a detailed error when the packaged engine is missing rather than silently using an ambient Python installation.

`tests/test_windows_runtime_contract.py` pins these three sides of the contract together: the workflow staging path, the Tauri resource mapping, and the Rust resource-root lookup. This test is intentionally cross-platform and does not install or execute the Windows bundle. The Windows Installer workflow remains responsible for building the real NSIS artifact and smoke-testing the standalone engine.

When changing any packaged-engine path, update all three surfaces in the same pull request and keep the contract test green.
