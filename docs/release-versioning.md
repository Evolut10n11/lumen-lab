# Desktop release versioning

Lumen's desktop product version is intentionally separate from the Python package version in `pyproject.toml`.

For a desktop release, the same semantic version must be present in:

- `apps/desktop/package.json`;
- `apps/desktop/src-tauri/Cargo.toml`;
- `apps/desktop/src-tauri/tauri.conf.json`.

`tauri.conf.json` is the release-facing version used to validate Git tags. A tagged release must use exactly `v<desktop-version>`; for example, desktop version `0.1.1` must be released from tag `v0.1.1`. The Windows Installer workflow fails before publishing if the tag and bundled desktop version disagree.

The README installer example must also match the current desktop version. `tests/test_release_version_contract.py` locks these relationships so a version bump cannot silently update only part of the release surface.

The Python package in `pyproject.toml` may evolve independently because it represents the engine/development package rather than the installed desktop application's release identity. Do not force the Python version to match the desktop version unless that coupling becomes an explicit product decision.
