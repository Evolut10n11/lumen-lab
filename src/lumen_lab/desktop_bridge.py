from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .app_service import LumenApplication
from .onboarding import (
    apply_focus_minutes,
    guided_profile_inputs,
    load_onboarding_context,
    onboarding_context_payload,
    save_onboarding_context,
)


def _payload(request: dict[str, Any]) -> dict[str, Any]:
    payload = request.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    return payload


def _dashboard_with_context(
    app: LumenApplication,
    user_id: str | None,
    *,
    top: int = 3,
) -> dict[str, Any]:
    dashboard = app.dashboard(user_id, top=top)
    workspace = app.workspace(user_id)
    dashboard["context"] = load_onboarding_context(workspace.onboarding_context_path)
    return dashboard


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
        result = app.bootstrap(user_id, top=int(payload.get("top", 3)))
        if result["initialized"]:
            workspace = app.workspace(result["selected_user_id"])
            result["context"] = load_onboarding_context(workspace.onboarding_context_path)
        else:
            result["context"] = None
        return result

    if action == "dashboard":
        return _dashboard_with_context(app, user_id, top=int(payload.get("top", 3)))

    if action == "guided_onboard":
        display_name = payload.get("display_name")
        current_context = payload.get("current_context")
        desired_change = payload.get("desired_change")
        friction = payload.get("friction", "")
        focus_minutes = payload.get("focus_minutes", 30)
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("display_name must be a non-empty string")
        if not isinstance(current_context, str):
            raise ValueError("current_context must be a string")
        if not isinstance(desired_change, str):
            raise ValueError("desired_change must be a string")
        if not isinstance(friction, str):
            raise ValueError("friction must be a string")
        if isinstance(focus_minutes, bool) or not isinstance(focus_minutes, int):
            raise ValueError("focus_minutes must be an integer")
        if user_id is None:
            raise ValueError("guided_onboard requires user_id")

        inputs = guided_profile_inputs(
            current_context=current_context,
            desired_change=desired_change,
            friction=friction,
            focus_minutes=focus_minutes,
        )
        app.onboard(
            user_id,
            display_name=display_name,
            priorities=inputs["priorities"],
            interests=inputs["interests"],
            constraints=inputs["constraints"],
            replace=bool(payload.get("replace", False)),
        )
        workspace = app.workspace(user_id)
        apply_focus_minutes(workspace.work_sessions_path, inputs["focus_minutes"])
        context = onboarding_context_payload(
            current_context=current_context,
            desired_change=desired_change,
            friction=friction,
            focus_minutes=inputs["focus_minutes"],
        )
        save_onboarding_context(workspace.onboarding_context_path, context)
        return _dashboard_with_context(app, user_id)

    if action == "quick_onboard":
        display_name = payload.get("display_name")
        goals = payload.get("goals")
        if not isinstance(display_name, str) or not display_name.strip():
            raise ValueError("display_name must be a non-empty string")
        if not isinstance(goals, list) or not all(isinstance(item, str) for item in goals):
            raise ValueError("goals must be a JSON list of strings")
        if user_id is None:
            raise ValueError("quick_onboard requires user_id")
        app.quick_onboard(
            user_id,
            display_name=display_name,
            goals=goals,
            replace=bool(payload.get("replace", False)),
        )
        return _dashboard_with_context(app, user_id)

    if action == "react":
        reaction = payload.get("reaction")
        mission_id = payload.get("mission_id")
        if not isinstance(reaction, str):
            raise ValueError("reaction must be a string")
        if mission_id is not None and not isinstance(mission_id, str):
            raise ValueError("mission_id must be a string or null")
        app.react_to_mission(
            reaction,
            user_id,
            mission_id=mission_id,
            top=int(payload.get("top", 3)),
        )
        return _dashboard_with_context(app, user_id, top=int(payload.get("top", 3)))

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
