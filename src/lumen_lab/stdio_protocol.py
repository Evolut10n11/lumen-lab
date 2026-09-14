from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

from .unicode_safety import sanitize_json_strings


def read_request() -> dict[str, Any]:
    """Decode the wire bytes, never the process/Windows default text encoding."""
    stream = sys.stdin
    if stream is None:
        raise ValueError("Lumen engine has no request input stream")
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        try:
            raw = buffer.read().decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"Lumen request is not valid UTF-8 at byte {exc.start}"
            ) from exc
    else:
        # Embedded callers/tests may supply StringIO instead of an OS pipe.
        raw = stream.read().removeprefix("\ufeff")
    if not raw.strip():
        raise ValueError("Lumen engine received an empty request")
    request = json.loads(raw)
    if not isinstance(request, dict):
        raise ValueError("desktop request must be a JSON object")
    return sanitize_json_strings(request)


def write_response(response: dict[str, Any]) -> None:
    """Emit JSON as explicit UTF-8 bytes; Unicode escapes are lossless JSON."""
    # ASCII JSON also protects text-only embeddings with a legacy codec. This is
    # escaping, NOT errors='replace': Cyrillic and emoji decode without any loss.
    text = json.dumps(sanitize_json_strings(response), ensure_ascii=True) + "\n"
    stream = sys.stdout
    if stream is None:
        raise OSError("Lumen engine has no response output stream")
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        buffer.write(text.encode("utf-8", errors="strict"))
        buffer.flush()
    else:
        stream.write(text)
        stream.flush()


def serve(dispatch: Callable[[dict[str, Any]], dict[str, Any]]) -> int:
    """Serve one request and keep diagnostics out of the JSON response channel."""
    try:
        response = {"ok": True, "data": dispatch(read_request())}
    except (OSError, ValueError, TypeError) as exc:
        response = {
            "ok": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
    write_response(response)
    return 0 if response["ok"] else 2
