import argparse
import json
import os
import sys
from pathlib import Path

import pytest

from lumen_lab.capabilities import (
    DEFAULT_MAX_OUTPUT_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    CapabilityError,
    CapabilityManifest,
    get_manifest,
    load_capability_manifests,
    render_manifest_list,
    resolve_execution_policy,
    run_with_policy,
)
from lumen_lab.capabilities_cli import cmd_run


def _write(path: Path, manifests: list[dict[str, object]]) -> Path:
    path.write_text(
        json.dumps({"manifests": manifests}),
        encoding="utf-8",
    )
    return path


def _manifest(name: str, executable: str = "python") -> dict[str, object]:
    return {
        "name": name,
        "description": f"{name} profile",
        "executables": [executable],
        "timeout_seconds": 2.0,
        "max_output_bytes": 4096,
    }


def test_loader_validates_and_sorts_manifests(tmp_path) -> None:
    path = _write(
        tmp_path / "capabilities.json",
        [_manifest("zeta"), _manifest("alpha")],
    )

    manifests = load_capability_manifests(path)

    assert [item.name for item in manifests] == ["alpha", "zeta"]


def test_loader_rejects_duplicate_manifest_names(tmp_path) -> None:
    path = _write(
        tmp_path / "capabilities.json",
        [_manifest("same"), _manifest("same")],
    )

    with pytest.raises(CapabilityError, match="duplicate capability manifest name"):
        load_capability_manifests(path)


def test_manifest_reuses_sandbox_path_rejection(tmp_path) -> None:
    path = _write(
        tmp_path / "capabilities.json",
        [_manifest("unsafe", "../python")],
    )

    with pytest.raises(CapabilityError, match="path-like executable names"):
        load_capability_manifests(path)


def test_missing_manifest_is_rejected() -> None:
    with pytest.raises(CapabilityError, match="unknown capability manifest"):
        get_manifest([], "missing")


def test_render_manifest_list_is_deterministic() -> None:
    manifests = [
        CapabilityManifest("zeta", ("python",), 2.0, 4096, "z"),
        CapabilityManifest("alpha", ("python",), 2.0, 4096, "a"),
    ]

    rendered = render_manifest_list(manifests)

    assert rendered.index("alpha") < rendered.index("zeta")


def test_manifest_policy_rejects_manual_overrides() -> None:
    manifests = [CapabilityManifest("python-basic", ("python",), 2.0, 4096)]

    with pytest.raises(CapabilityError, match="cannot be combined"):
        resolve_execution_policy(
            manifests,
            manifest_name="python-basic",
            manual_allowed=("python",),
        )

    with pytest.raises(CapabilityError, match="cannot be combined"):
        resolve_execution_policy(
            manifests,
            manifest_name="python-basic",
            timeout_override=1.0,
        )


def test_manual_policy_preserves_existing_defaults() -> None:
    policy = resolve_execution_policy([], manual_allowed=("python",))

    assert policy.source == "manual"
    assert policy.allowed_executables == ("python",)
    assert policy.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
    assert policy.max_output_bytes == DEFAULT_MAX_OUTPUT_BYTES


def test_cli_rejects_manifest_and_manual_allow_conflict(tmp_path) -> None:
    path = _write(
        tmp_path / "capabilities.json",
        [_manifest("python-basic")],
    )
    args = argparse.Namespace(
        file=str(path),
        manifest="python-basic",
        allow=["python"],
        timeout=None,
        max_output_bytes=None,
        json=False,
        argv=["--", "python", "-c", "print('nope')"],
    )

    with pytest.raises(SystemExit, match="cannot be combined"):
        cmd_run(args)


def test_execution_through_manifest() -> None:
    executable = Path(sys.executable).name
    manifest = CapabilityManifest(
        name="python-test",
        executables=(executable,),
        timeout_seconds=2.0,
        max_output_bytes=4096,
    )
    manifest.validate()
    policy = resolve_execution_policy(
        [manifest],
        manifest_name="python-test",
    )

    result = run_with_policy(
        [executable, "-c", "print('manifest-ok')"],
        policy,
    )

    assert result.ok
    assert result.stdout.strip() == "manifest-ok"
    assert os.path.basename(result.resolved_executable) == executable
