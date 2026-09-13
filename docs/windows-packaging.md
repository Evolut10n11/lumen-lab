# Windows packaging contract

The Windows desktop build has two executables with different jobs:

- the Tauri host (`Lumen.exe`) owns the desktop window and IPC boundary;
- the standalone Python engine (`lumen-engine.exe`) serves the local JSON bridge used by the host.

The installer build creates `lumen-engine.exe` with PyInstaller, smoke-tests it directly, then stages it at `apps/desktop/src-tauri/resources/lumen-engine.exe` before Tauri builds the NSIS installer.

`apps/desktop/src-tauri/tauri.windows.conf.json` maps that staged source to `lumen-engine.exe` at the Tauri resource root. The Rust host resolves `lumen-engine.exe` relative to `BaseDirectory::Resource` in release builds. Development builds may fall back to `python -m lumen_lab.desktop_bridge`, but release builds must fail with a detailed error when the packaged engine is missing rather than silently using an ambient Python installation.

`tests/test_windows_runtime_contract.py` pins the packaging surfaces together: the workflow staging path, the Tauri resource mapping, the Rust resource-root lookup, and the installed-bundle smoke-test contract.

The Windows Installer workflow performs two runtime checks on `windows-latest`:

1. it executes the standalone PyInstaller engine before bundling;
2. after Tauri produces the real NSIS artifact, it silently installs that artifact into an isolated temporary directory, locates `lumen-engine.exe` from the installed files, and runs a bootstrap request through that installed executable.

The second check is important because it catches resource-mapping and installer-layout regressions that a pre-bundle smoke test cannot detect. It is still not a substitute for exploratory UI testing on a normal end-user Windows machine, but packaged-engine startup no longer depends solely on that manual check.

When changing any packaged-engine path, installer type, or runtime lookup behavior, update all four surfaces in the same pull request and keep the contract test and Windows Installer workflow green.
