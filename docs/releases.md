# GitHub Releases

Lumen publishes a Windows installer from the same CI pipeline that builds and smoke-tests the packaged application.

## Release rule

The desktop version in `apps/desktop/src-tauri/tauri.conf.json` is the release version source of truth.

On a push to `main` that triggers the Windows Installer workflow:

1. the standalone engine is built and smoke-tested;
2. the NSIS installer is built;
3. the installer is silently installed on a clean Windows runner and the bundled engine is smoke-tested from the installed files;
4. if a GitHub Release for `v<desktop-version>` does not exist yet, the workflow creates it and uploads the installer;
5. if that release already exists, publishing is skipped so an immutable version is not silently replaced.

Tag-triggered releases remain supported and are validated against the desktop version.

## Versioning

Before publishing a new public build, bump the desktop version first. A new version such as `0.1.2` will produce release `v0.1.2` on the first qualifying push to `main`.
