from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .app_service import LumenApplication


def _payload(request: dict[str, Any]) -> dict[str, Any]:
    payload = request.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    return payload


def dispatch(request: dict[str, Any]) -> dict[str, Any]:
    """Dispatch one desktop request to the product-facing application service.

    The desktop state root is deliberately host-controlled. The Tauri process chooses
    the Python subprocess working directory, and webview input cannot override it.
    """
    action = request.get("action")
    if not isinstance(action, str) or not action.strip():
        raise ValueError("action must be a non-empty string")

    root = Path.cwd()
    user_id = request.get("user_id")
    if user_id is not None and not isinstance(user_id, str):
        raise ValueError("user_id must be a string or null")

    app = LumenApplication(root)
    payload = _payload(request)
    action = action.strip().casefold()

    if action == "bootstrap":
        return app.bootstrap(user_id, top=int(payload.get("top", 3)))

    if action == "dashboard":
        return app.dashboard(user_id, top=int(payload.get("top", 3)))

    if action == "quick_onboard":
        display_name = payload.get("display_name")
        goals = payload.get("goals")
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("display_name must be a non-empty string")
        if not isinstance(goals, list) or not all(isinstance(item, str) for item in goals):
            raise ValueError("goals must be a JSON list of strings")
        if user_id is None:
            raise ValueError("quick_onboard requires user_id")
        return app.quick_onboard(
            user_id,
            display_name=display_name,
            goals=goals,
            replace=bool(payload.get("replace", False)),
        )

    if action == "react":
        reaction = payload.get("reaction")
        mission_id = payload.get("mission_id")
        if not isinstance(reaction, str):
            raise ValueError("reaction must be a string")
        if mission_id is not None and not isinstance(mission_id, str):
            raise ValueError("mission_id must be a string or null")
        return app.react_to_mission(
            reaction,
            user_id,
            mission_id=mission_id,
            top=int(payload.get("top", 3)),
        )

    if action == "complete_step":
        step = payload.get("step")
        mission_id = payload.get("mission_id")
        if isinstance(step, bool) or not isinstance(step, int):
            raise ValueError("step must be an integer")
        if mission_id is not None and not isinstance(mission_id, str):
            raise ValueError("mission_id must be a string or null")
        return app.complete_step(step, user_id, mission_id=mission_id)

    raise ValueError(f"unsupported desktop action: {action}")


def _response_ok(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": data}


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
        response = _response_ok(dispatch(request))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        response = _response_error(exc)

    sys.stdout.write(json.dumps(response, ensure_ascii=False))
    sys.stdout.flush()
    return 0 if response["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
