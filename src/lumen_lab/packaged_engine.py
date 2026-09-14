from __future__ import annotations

import json
import sys
from typing import Any

from .desktop_bridge import dispatch
from .unicode_safety import sanitize_json_strings


def _response_error(exc: Exception) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "type": exc.__class__.__name__,
            "message": str(exc),
        },
    }


def main() -> int:
    try:
        raw = sys.stdin.read()
        request = json.loads(raw)
        if not isinstance(request, dict):
            raise ValueError("desktop request must be a JSON object")
        request = sanitize_json_strings(request)
        response: dict[str, Any] = {"ok": True, "data": dispatch(request)}
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        response = _response_error(exc)

    response = sanitize_json_strings(response)
    sys.stdout.write(json.dumps(response, ensure_ascii=False))
    sys.stdout.flush()
    return 0 if response["ok"] else 2
