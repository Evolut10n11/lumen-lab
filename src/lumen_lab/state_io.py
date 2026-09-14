from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

_LOCK_TIMEOUT_SECONDS = 10.0
_LOCK_RETRY_SECONDS = 0.05


def _try_lock(stream: Any) -> None:
    stream.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(stream: Any) -> None:
    stream.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _acquire_lock(stream: Any) -> None:
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
    while True:
        try:
            _try_lock(stream)
            return
        except OSError as error:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("timed out waiting for Lumen workspace lock") from error
            time.sleep(min(_LOCK_RETRY_SECONDS, remaining))


def fsync_parent_directory(path: Path) -> None:
    """Persist a completed rename on filesystems that support directory fsync."""

    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path.parent, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def json_path_lock(path: Path) -> Iterator[None]:
    """Serialize JSON state access within one workspace across processes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / ".lumen-json.lock"
    with lock_path.open("a+b") as stream:
        if os.name == "nt":
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
        _acquire_lock(stream)
        try:
            yield
        finally:
            _unlock(stream)


def write_json_atomic_unlocked(path: Path, payload: Any) -> None:
    """Replace JSON atomically while the caller holds ``json_path_lock``."""

    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    # Encode before opening a file so malformed Unicode cannot truncate existing state.
    data = text.encode("utf-8")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_parent_directory(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json_atomic(path: Path, payload: Any) -> None:
    """Write UTF-8 JSON atomically and serialize all cooperating writers."""

    with json_path_lock(path):
        write_json_atomic_unlocked(path, payload)
