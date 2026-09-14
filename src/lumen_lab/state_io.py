from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


def write_json_atomic(path: Path, payload: Any) -> None:
    """Write UTF-8 JSON without ever truncating the previous valid file first."""

    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    # Encode before opening a file so malformed Unicode cannot truncate existing state.
    data = text.encode("utf-8")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
