from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

GUARD = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'packaging/check_release.py'))


def manifests(
    root: Path,
    cargo_version: str = '0.1.3',
    lock_version: str = '0.1.3',
) -> None:
    desktop = root / 'apps/desktop'
    (desktop / 'src-tauri').mkdir(parents=True)
    for name in ('package.json', 'src-tauri/tauri.conf.json'):
        (desktop / name).write_text(json.dumps({'version': '0.1.3'}), encoding='utf-8')
    (desktop / 'package-lock.json').write_text(
        json.dumps({'version': lock_version, 'packages': {'': {'version': lock_version}}}),
        encoding='utf-8',
    )
    (desktop / 'src-tauri/Cargo.toml').write_text(
        f'[package]\nversion = "{cargo_version}"\n', encoding='utf-8',
    )


@pytest.mark.parametrize('ref', ['refs/heads/main', 'refs/tags/v0.1.3'])
def test_matching_release_version(tmp_path, ref):
    manifests(tmp_path)
    assert GUARD['validate_versions'](tmp_path, ref) == 'v0.1.3'


@pytest.mark.parametrize('ref', ['refs/tags/V0.1.3', 'refs/tags/v0.1.2'])
def test_rejects_wrong_or_case_mismatched_tag(tmp_path, ref):
    manifests(tmp_path)
    with pytest.raises(ValueError, match='does not match'):
        GUARD['validate_versions'](tmp_path, ref)


def test_rejects_inconsistent_manifests(tmp_path):
    manifests(tmp_path, cargo_version='0.1.2')
    with pytest.raises(ValueError, match='disagree'):
        GUARD['validate_versions'](tmp_path, 'refs/heads/main')


def test_rejects_lockfile_version_drift(tmp_path):
    manifests(tmp_path, lock_version='0.1.2')
    with pytest.raises(ValueError, match='disagree'):
        GUARD['validate_versions'](tmp_path, 'refs/heads/main')


@pytest.mark.parametrize('output', [
    '', 'abc\trefs/tags/v0.1.3\n',
    'tag-object\trefs/tags/v0.1.3\nabc\trefs/tags/v0.1.3^{}\n',
])
def test_allows_absent_or_matching_lightweight_and_annotated_tags(output):
    GUARD['validate_remote_tag'](output, 'v0.1.3', 'abc')


@pytest.mark.parametrize('output', [
    'wrong\trefs/tags/v0.1.3\n',
    'abc\trefs/tags/v0.1.3\nwrong\trefs/tags/v0.1.3^{}\n',
])
def test_rejects_tag_pointing_to_another_commit(output):
    with pytest.raises(ValueError, match='not build commit'):
        GUARD['validate_remote_tag'](output, 'v0.1.3', 'abc')


def test_accepts_semver_build_metadata(tmp_path):
    manifests(tmp_path)
    version = '0.1.3+desktop.1'
    desktop = tmp_path / 'apps/desktop'
    for name in ('package.json', 'src-tauri/tauri.conf.json'):
        (desktop / name).write_text(json.dumps({'version': version}), encoding='utf-8')
    (desktop / 'package-lock.json').write_text(
        json.dumps({'version': version, 'packages': {'': {'version': version}}}),
        encoding='utf-8',
    )
    (desktop / 'src-tauri/Cargo.toml').write_text(
        f'[package]\nversion = "{version}"\n', encoding='utf-8',
    )
    assert GUARD['validate_versions'](tmp_path, f'refs/tags/v{version}') == f'v{version}'
