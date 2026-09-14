# GitHub Releases

Lumen publishes a Windows installer from the same CI pipeline that builds and smoke-tests the packaged application.

## Release rule

The desktop version in `apps/desktop/src-tauri/tauri.conf.json` is the release version source of truth.

On a push to `main` that triggers the Windows Installer workflow:

1. the standalone engine is built and smoke-tested;
2. the NSIS installer is built;
3. the installer is silently installed on a clean Windows runner and the bundled engine is smoke-tested from the installed files;
4. the exact smoke-tested installer receives a SHA-256 checksum, and both files are carried through the workflow artifact;
5. after the artifact is downloaded by the publish job, `sha256sum --check` verifies that the installer still matches the generated checksum;
6. if a GitHub Release for `v<desktop-version>` does not exist yet, the workflow creates it, publishes `docs/release-notes-v<desktop-version>.md` when present (or generated notes otherwise), and uploads both the installer and its `.sha256` checksum;
7. if that release already exists, publishing is skipped so an immutable version is not silently replaced.

Tag-triggered releases remain supported and are validated against the desktop version.

## Verifying a download

Each new release produced by this workflow contains the installer and a matching `.sha256` file. The checksum file uses the standard `sha256sum` format: a lowercase SHA-256 digest, two spaces, and the installer filename.

On Linux, macOS with GNU coreutils, or another environment with `sha256sum`, put both files in the same directory and run:

```bash
sha256sum --check *.sha256
```

On Windows PowerShell, compare the first field in the checksum file with `Get-FileHash -Algorithm SHA256` for the downloaded installer. A mismatch means the installer must not be trusted or executed.

The checksum is generated only after the same installer has passed the installed-bundle smoke test, and the publish job verifies it again after the GitHub Actions artifact transfer. Existing releases are never rewritten merely to add checksums.

## Versioning

Before publishing a new public build, bump the desktop version first. A new version such as `0.2.1` will produce release `v0.2.1` on the first qualifying push to `main`.
