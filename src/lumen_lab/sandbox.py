from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


class SandboxError(ValueError):
    """Raised when a sandbox request violates the local execution policy."""


@dataclass(slots=True, frozen=True)
class SandboxResult:
    argv: tuple[str, ...]
    resolved_executable: str
    returncode: int | None
    timed_out: bool
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    working_directory: str
    duration_ms: int

    @property
    def ok(self) -> bool:
        return not self.timed_out and self.returncode == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "argv": list(self.argv),
            "resolved_executable": self.resolved_executable,
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "ok": self.ok,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
            "working_directory": self.working_directory,
            "duration_ms": self.duration_ms,
        }


class _BoundedCollector(threading.Thread):
    def __init__(self, stream: BinaryIO, limit: int) -> None:
        super().__init__(daemon=True)
        self._stream = stream
        self._limit = limit
        self._data = bytearray()
        self.truncated = False

    def run(self) -> None:
        while True:
            chunk = self._stream.read(8192)
            if not chunk:
                return
            remaining = self._limit - len(self._data)
            if remaining > 0:
                self._data.extend(chunk[:remaining])
            if len(chunk) > max(remaining, 0):
                self.truncated = True

    def text(self) -> str:
        return bytes(self._data).decode("utf-8", errors="replace")


def _validate_bare_executable(name: str) -> None:
    if not name or name in {".", ".."}:
        raise SandboxError("executable name must be a non-empty bare command name")
    if "/" in name or "\\" in name or ":" in name:
        raise SandboxError("path-like executable names are not allowed")


def _minimal_environment(workspace: Path, resolved_executable: str) -> dict[str, str]:
    executable_dir = str(Path(resolved_executable).resolve().parent)
    return {
        "HOME": str(workspace),
        "USERPROFILE": str(workspace),
        "TMP": str(workspace),
        "TEMP": str(workspace),
        "TMPDIR": str(workspace),
        "PATH": executable_dir,
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
        "LUMEN_SANDBOX": "1",
    }


def run_sandboxed(
    argv: Sequence[str],
    *,
    allowed_executables: Collection[str],
    timeout_seconds: float = 5.0,
    max_output_bytes: int = 64 * 1024,
) -> SandboxResult:
    """Run one explicitly allowed command with bounded I/O and a minimal environment.

    This is process containment for controlled experiments, not an OS security boundary.
    The child still has the operating-system permissions of the current user.
    """

    if not argv:
        raise SandboxError("command argv must not be empty")
    if timeout_seconds <= 0 or timeout_seconds > 60:
        raise SandboxError("timeout_seconds must be greater than 0 and at most 60")
    if max_output_bytes <= 0 or max_output_bytes > 1_000_000:
        raise SandboxError("max_output_bytes must be between 1 and 1000000")

    executable = argv[0]
    _validate_bare_executable(executable)

    normalized_allowed: set[str] = set()
    for allowed in allowed_executables:
        _validate_bare_executable(allowed)
        normalized_allowed.add(os.path.normcase(allowed))
    if os.path.normcase(executable) not in normalized_allowed:
        raise SandboxError(f"executable is not allowed: {executable}")

    resolved = shutil.which(executable)
    if resolved is None:
        raise SandboxError(f"allowed executable was not found on PATH: {executable}")

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="lumen-sandbox-") as temp_dir:
        workspace = Path(temp_dir).resolve()
        environment = _minimal_environment(workspace, resolved)
        process = subprocess.Popen(
            [resolved, *argv[1:]],
            cwd=workspace,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        if process.stdout is None or process.stderr is None:
            process.kill()
            process.wait()
            raise SandboxError("failed to capture sandbox output")

        stdout_collector = _BoundedCollector(process.stdout, max_output_bytes)
        stderr_collector = _BoundedCollector(process.stderr, max_output_bytes)
        stdout_collector.start()
        stderr_collector.start()

        timed_out = False
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
        finally:
            stdout_collector.join()
            stderr_collector.join()
            process.stdout.close()
            process.stderr.close()

        duration_ms = int((time.monotonic() - started) * 1000)
        return SandboxResult(
            argv=tuple(argv),
            resolved_executable=str(Path(resolved).resolve()),
            returncode=process.returncode,
            timed_out=timed_out,
            stdout=stdout_collector.text(),
            stderr=stderr_collector.text(),
            stdout_truncated=stdout_collector.truncated,
            stderr_truncated=stderr_collector.truncated,
            working_directory=str(workspace),
            duration_ms=duration_ms,
        )
