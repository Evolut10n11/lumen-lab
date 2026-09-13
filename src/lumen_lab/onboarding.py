from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .profile import normalized_label

ONBOARDING_CONTEXT_VERSION = 1
ALLOWED_FOCUS_MINUTES = (15, 30, 60)
_MAX_ANSWER_LENGTH = 1200

_PREFIXES = (
    r"i\s+(?:really\s+)?(?:want|need|would\s+like)\s+to\s+",
    r"i(?:'m|\s+am)\s+trying\s+to\s+",
    r"my\s+goal\s+is\s+(?:to\s+)?",
    r"я\s+(?:очень\s+)?хочу\s+",
    r"хочу\s+",
    r"мне\s+нужно\s+",
    r"я\s+пытаюсь\s+",
    r"моя\s+цель\s*(?:[-—:]\s*)?",
)
_GOAL_PREFIX_RE = re.compile(rf"^(?:{'|'.join(_PREFIXES)})", re.IGNORECASE)


def _clean_answer(value: str, name: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    cleaned = " ".join(value.strip().split())
    if required and not cleaned:
        raise ValueError(f"{name} must be a non-empty string")
    if len(cleaned) > _MAX_ANSWER_LENGTH:
        raise ValueError(f"{name} must be {_MAX_ANSWER_LENGTH} characters or fewer")
    return cleaned


def _validated_focus_minutes(value: int) -> int:
    if isinstance(value, bool) or value not in ALLOWED_FOCUS_MINUTES:
        allowed = ", ".join(str(item) for item in ALLOWED_FOCUS_MINUTES)
        raise ValueError(f"focus_minutes must be one of: {allowed}")
    return value


def goal_label(value: str) -> str:
    """Turn a normal first-person answer into a concise goal label when possible."""
    cleaned = _clean_answer(value, "desired_change")
    label = _GOAL_PREFIX_RE.sub("", cleaned, count=1).strip(" .,!?:;\"'“”«»")
    if not label:
        label = cleaned
    if label and label[0].islower():
        label = label[0].upper() + label[1:]
    return label


def guided_profile_inputs(
    *,
    current_context: str,
    desired_change: str,
    friction: str = "",
    focus_minutes: int = 30,
) -> dict[str, Any]:
    """Infer conservative starter profile inputs from a short first-run conversation."""
    context = _clean_answer(current_context, "current_context")
    change = _clean_answer(desired_change, "desired_change")
    blocker = _clean_answer(friction, "friction", required=False)
    focus_minutes = _validated_focus_minutes(focus_minutes)

    primary_goal = goal_label(change)
    interests: tuple[str, ...] = ()
    if normalized_label(context) != normalized_label(primary_goal):
        interests = (context,)

    return {
        "priorities": {primary_goal: 10},
        "interests": interests,
        "constraints": (blocker,) if blocker else (),
        "focus_minutes": focus_minutes,
    }


def onboarding_context_payload(
    *,
    current_context: str,
    desired_change: str,
    friction: str = "",
    focus_minutes: int = 30,
) -> dict[str, Any]:
    """Persist raw answers separately from the profile so later learning can revise hypotheses."""
    inputs = guided_profile_inputs(
        current_context=current_context,
        desired_change=desired_change,
        friction=friction,
        focus_minutes=focus_minutes,
    )
    context = _clean_answer(current_context, "current_context")
    change = _clean_answer(desired_change, "desired_change")
    blocker = _clean_answer(friction, "friction", required=False)
    goal = next(iter(inputs["priorities"]))

    hypotheses: list[dict[str, Any]] = [
        {
            "key": "primary_goal",
            "label": "What you want to change",
            "value": goal,
            "confidence": 0.78,
            "source": "first_run_explicit_goal",
        },
        {
            "key": "current_context",
            "label": "What has your attention now",
            "value": context,
            "confidence": 0.86,
            "source": "first_run_explicit_context",
        },
        {
            "key": "focus_window",
            "label": "Realistic focus window",
            "value": f"{focus_minutes} minutes",
            "confidence": 0.95,
            "source": "first_run_explicit_choice",
        },
    ]
    if blocker:
        hypotheses.append(
            {
                "key": "friction",
                "label": "What tends to get in the way",
                "value": blocker,
                "confidence": 0.82,
                "source": "first_run_explicit_constraint",
            }
        )

    return {
        "version": ONBOARDING_CONTEXT_VERSION,
        "source": "conversation",
        "answers": {
            "current_context": context,
            "desired_change": change,
            "friction": blocker or None,
            "focus_minutes": focus_minutes,
        },
        "hypotheses": hypotheses,
        "average_confidence": round(
            sum(item["confidence"] for item in hypotheses) / len(hypotheses),
            2,
        ),
    }


def save_onboarding_context(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_onboarding_context(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("onboarding context must contain a JSON object")
    return raw


def apply_focus_minutes(path: Path, focus_minutes: int) -> None:
    """Tune generated work sessions to the focus window chosen in first-run setup."""
    focus_minutes = _validated_focus_minutes(focus_minutes)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("work sessions state must contain a JSON list")
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("work session entries must be JSON objects")
        item["focus_minutes"] = focus_minutes
    path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
