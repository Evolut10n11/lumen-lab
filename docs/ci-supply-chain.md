# CI supply-chain policy

Lumen treats GitHub Actions and build toolchains as executable dependencies. External actions in `.github/workflows/` must therefore be pinned to immutable 40-character commit SHAs rather than mutable tags or branches, the desktop Rust compiler must be selected by the repository-owned `rust-toolchain.toml` rather than a floating `stable` channel, and desktop JavaScript dependencies must be installed from the committed npm lockfile.

The workflow line should keep the reviewed major tag as an inline comment, for example:

```yaml
- uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
```

The Rust toolchain is pinned separately:

```toml
[toolchain]
channel = "1.98.1"
profile = "minimal"
```

Desktop dependency installs are lockfile-driven:

```bash
cd apps/desktop
npm ci
```

## Why

A reference such as `actions/checkout@v4` can move after a pull request has been reviewed. Likewise, `rustup update stable` can select a different compiler on two otherwise identical CI runs, and `npm install` can resolve newer package versions that still satisfy dependency ranges. Pinning the exact action revisions and Rust version, plus committing `apps/desktop/package-lock.json` and using `npm ci`, makes the build environment more stable and auditable.

This is especially important for workflows with write permissions or release responsibilities. Pinning does not make an action, compiler, or dependency trustworthy by itself; it makes the selected revision explicit and reviewable.

## Updating an action

1. Resolve the desired official release or maintained major tag in the action's upstream repository.
2. Review the upstream release notes and the exact commit being selected.
3. Replace the pinned SHA and update the inline version comment if the major version changed.
4. Let the normal pull-request CI run before merging.

`tests/test_workflow_action_pinning.py` scans every YAML workflow and fails if an external `uses:` entry uses a mutable ref. Repository-local actions (`./...`) and `docker://` references are excluded from this specific rule because they have different provenance semantics.

## Updating Rust

1. Select an explicit stable Rust release after reviewing its official release notes, including any point-release fixes.
2. Change `channel` in `rust-toolchain.toml` to that exact version.
3. Update `EXPECTED_RUST_VERSION` in `tests/test_rust_toolchain_contract.py` in the same pull request.
4. Do not add `rustup update stable` or `rustup default stable` to desktop workflows; rustup discovers the repository toolchain file automatically.
5. Require both Desktop CI and the Windows Installer build/smoke test to pass before merging.

`tests/test_rust_toolchain_contract.py` ensures the pin remains exact and that both desktop workflows watch `rust-toolchain.toml` without reintroducing a floating stable-channel override.

## Updating desktop npm dependencies

1. Change dependency declarations in `apps/desktop/package.json`.
2. Regenerate `apps/desktop/package-lock.json` with the repository's Node 22 toolchain and review the resulting lockfile diff.
3. Keep `package.json` and `package-lock.json` in the same pull request.
4. Use `npm ci`, not `npm install`, in Desktop CI and Windows packaging workflows. `npm ci` must fail rather than silently rewriting an out-of-sync lockfile.
5. Require both Desktop CI and the Windows Installer build/smoke test to pass before merging dependency changes.

`tests/test_npm_lockfile_contract.py` checks that the lockfile exists, matches the desktop package name/version and declared top-level dependencies, and that packaging workflows do not reintroduce `npm install`.

The initial action pins were resolved from the official upstream major tags on 2026-09-14:

- `actions/checkout` v4 → `11d5960a326750d5838078e36cf38b85af677262`
- `actions/setup-python` v5 → `a26af69be951a213d495a4c3e4e4022e16d87065`
- `actions/setup-node` v4 → `49933ea5288caeca8642d1e84afbd3f7d6820020`
- `actions/upload-artifact` v4 → `ea165f8d65b6e75b540449e92b4886f43607fa02`
- `actions/download-artifact` v4 → `d3f86a106a0bac45b974a628896c90dbdf5c8093`

The initial Rust pin is `1.98.1`, selected on 2026-09-14.
