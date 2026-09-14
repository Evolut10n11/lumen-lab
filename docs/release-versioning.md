# Desktop release versioning

Lumen's desktop product version is intentionally separate from the Python package version in `pyproject.toml`.

For a desktop release, the same semantic version must be present in:

- `apps/desktop/package.json`;
- the top-level and root-package version metadata in `apps/desktop/package-lock.json`;
- `apps/desktop/src-tauri/Cargo.toml`;
- `apps/desktop/src-tauri/tauri.conf.json`.

`tauri.conf.json` is the release-facing version used to validate Git tags. A tagged release must use exactly `v<desktop-version>`; for example, desktop version `0.2.0` must be released from tag `v0.2.0`. The Windows Installer workflow validates every listed desktop manifest before building and compares tagged release names case-sensitively. Before creating a new release, it checks the remote tag against the exact build commit, including peeled annotated tags. A tag pointing to another commit or a failed remote lookup stops publication. Existing releases remain unchanged. The shared guard is `packaging/check_release.py`.

The npm lockfile mirrors the package version in addition to locking the dependency graph. Version bumps should therefore update `package.json` and `package-lock.json` together; `tests/test_npm_lockfile_contract.py` and `tests/test_release_version_contract.py` both guard against metadata drift.

The README installer example must also match the current desktop version. `tests/test_release_version_contract.py` locks these relationships so a version bump cannot silently update only part of the release surface.

Patch releases that ship fixes already merged to `main` must advance the desktop version instead of replacing assets on an existing GitHub Release. This keeps published installers immutable from a user's point of view and makes it clear which build contains a given fix.

The Python package in `pyproject.toml` may evolve independently because it represents the engine/development package rather than the installed desktop application's release identity. Do not force the Python version to match the desktop version unless that coupling becomes an explicit product decision.
