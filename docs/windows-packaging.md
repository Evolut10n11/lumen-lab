# Windows packaging contract

The Windows desktop build has two executables with different jobs:

- the Tauri host (`lumen-desktop.exe`) owns the desktop window and IPC boundary;
- the standalone Python engine (`lumen-engine.exe`) serves the local JSON bridge used by the host.

The installer build creates `lumen-engine.exe` with PyInstaller, smoke-tests it directly, then stages it at `apps/desktop/src-tauri/resources/lumen-engine.exe` before Tauri builds the NSIS installer.

`apps/desktop/src-tauri/tauri.windows.conf.json` maps that staged source to `lumen-engine.exe` at the Tauri resource root. The Rust host resolves `lumen-engine.exe` relative to `BaseDirectory::Resource` in release builds. Development builds may fall back to `python -m lumen_lab.desktop_bridge`, but release builds must fail with a detailed error when the packaged engine is missing rather than silently using an ambient Python installation.

`tests/test_windows_runtime_contract.py` pins the packaging surfaces together: the workflow staging path, the Tauri resource mapping, the Rust resource-root lookup, the host timeout, and the installed-bundle smoke-test contract.

The Windows Installer workflow performs three runtime checks on `windows-latest`:

1. it executes the standalone PyInstaller engine before bundling;
2. after Tauri produces the real NSIS artifact, it silently installs that artifact into an isolated temporary directory, locates `lumen-engine.exe` from the installed files, and runs a bootstrap request through that installed executable;
3. it launches the installed `lumen-desktop.exe`, waits through startup, verifies that the desktop process remains alive, and then shuts it down.

The installed checks catch resource-mapping, installer-layout, WebView startup, and immediate host crashes that a pre-bundle engine check cannot detect. They are still not a substitute for exploratory UI testing on a normal end-user Windows machine.

The host currently starts a fresh engine process for each request. It serializes requests that share the local state directory, runs the blocking work outside the async command runtime, drains stdin and output concurrently, and kills requests that exceed 45 seconds. The black-box engine contract prints median and maximum process latency in CI so a later move to a persistent service can be based on measurements.

When changing any packaged-engine path, installer type, or runtime lookup behavior, update all four surfaces in the same pull request and keep the contract test and Windows Installer workflow green.
