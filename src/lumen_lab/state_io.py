from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


@contextmanager
def json_path_lock(path: Path) -> Iterator[None]:
    """Serialize JSON state access within one workspace across processes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / ".lumen-json.lock"
    with lock_path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"\0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


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
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json_atomic(path: Path, payload: Any) -> None:
    """Write UTF-8 JSON atomically and serialize all cooperating writers."""

    with json_path_lock(path):
        write_json_atomic_unlocked(path, payload)
