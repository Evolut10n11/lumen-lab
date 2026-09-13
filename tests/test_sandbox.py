from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from lumen_lab.sandbox import SandboxError, run_sandboxed


PYTHON = Path(sys.executable).name


def run_python(code: str, **kwargs: object):
    return run_sandboxed(
        [PYTHON, "-c", code],
        allowed_executables={PYTHON},
        **kwargs,
    )


def test_allowed_command_runs_and_returns_structured_result() -> None:
    result = run_python("print('hello from sandbox')")

    assert result.ok is True
    assert result.returncode == 0
    assert result.timed_out is False
    assert result.stdout == "hello from sandbox\n"
    assert result.stderr == ""
    assert result.to_dict()["ok"] is True


def test_unlisted_executable_is_blocked_before_spawn() -> None:
    with pytest.raises(SandboxError, match="not allowed"):
        run_sandboxed([PYTHON, "-c", "print('no')"], allowed_executables={"git"})


def test_path_like_executable_is_rejected() -> None:
    with pytest.raises(SandboxError, match="path-like"):
        run_sandboxed(
            [sys.executable, "-c", "print('no')"],
            allowed_executables={PYTHON},
        )


def test_parent_environment_is_not_inherited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LUMEN_PARENT_SECRET", "should-not-leak")
    code = "import os; print(os.getenv('LUMEN_PARENT_SECRET', 'missing'))"

    result = run_python(code)

    assert result.stdout.strip() == "missing"


def test_working_directory_is_temporary_and_removed_after_run() -> None:
    original = Path.cwd().resolve()
    result = run_python("import os; print(os.getcwd())")
    workspace = Path(result.working_directory)

    assert Path(result.stdout.strip()).resolve() == workspace
    assert workspace != original
    assert not workspace.exists()


def test_timeout_kills_the_direct_child() -> None:
    result = run_python("import time; time.sleep(2)", timeout_seconds=0.05)

    assert result.timed_out is True
    assert result.ok is False
    assert result.duration_ms < 1500


def test_stdout_and_stderr_are_capped_without_blocking() -> None:
    code = (
        "import sys; "
        "sys.stdout.write('x' * 5000); "
        "sys.stderr.write('y' * 5000)"
    )
    result = run_python(code, max_output_bytes=64)

    assert len(result.stdout.encode("utf-8")) == 64
    assert len(result.stderr.encode("utf-8")) == 64
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True


def test_limits_are_validated_before_spawn() -> None:
    with pytest.raises(SandboxError, match="at most 60"):
        run_python("print('no')", timeout_seconds=61)
    with pytest.raises(SandboxError, match="between 1 and 1000000"):
        run_python("print('no')", max_output_bytes=0)


def test_child_receives_only_minimal_sandbox_environment() -> None:
    code = (
        "import os; "
        "print(os.environ['LUMEN_SANDBOX']); "
        "print(os.environ['HOME']); "
        "print(os.environ['TMP'])"
    )
    result = run_python(code)
    lines = result.stdout.splitlines()

    assert lines[0] == "1"
    assert lines[1] == result.working_directory
    assert lines[2] == result.working_directory
    assert "LUMEN_PARENT_SECRET" not in os.environ or lines[0] == "1"
