from __future__ import annotations

from pathlib import Path
from typing import Any

from .localization import is_russian, locale_from_context, normalize_locale
from .onboarding import ALLOWED_FOCUS_MINUTES, load_onboarding_context, save_onboarding_context
from .profile import normalized_label

_SIGNAL_DELTAS = {
    "more_like_this": 0.05,
    "less_like_this": -0.10,
    "mission_completed": 0.06,
    "not_now": 0.0,
}
_MIN_CONFIDENCE = 0.30
_MAX_CONFIDENCE = 0.98


def _clamp_confidence(value: float) -> float:
    return round(max(_MIN_CONFIDENCE, min(_MAX_CONFIDENCE, value)), 2)


def _hypothesis(context: dict[str, Any], key: str) -> dict[str, Any] | None:
    hypotheses = context.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        return None
    for item in hypotheses:
        if isinstance(item, dict) and item.get("key") == key:
            return item
    return None


def _recompute_average(context: dict[str, Any]) -> None:
    hypotheses = context.get("hypotheses", [])
    values = [
        float(item["confidence"])
        for item in hypotheses
        if isinstance(item, dict) and isinstance(item.get("confidence"), (int, float))
    ]
    context["average_confidence"] = round(sum(values) / len(values), 2) if values else 0.0


def _learning(context: dict[str, Any]) -> dict[str, Any]:
    raw = context.get("learning")
    if not isinstance(raw, dict):
        raw = {}
        context["learning"] = raw
    raw.setdefault("events", 0)
    raw.setdefault("primary_goal_support", 0)
    raw.setdefault("primary_goal_conflict", 0)
    raw.setdefault("primary_goal_deferrals", 0)
    raw.setdefault("last_mission_id", None)
    raw.setdefault("last_signal", None)
    raw.setdefault("snooze_until_event", 0)
    return raw


def _matches_primary_goal(context: dict[str, Any], mission_tags: list[str]) -> bool:
    goal = _hypothesis(context, "primary_goal")
    if not goal or not isinstance(goal.get("value"), str):
        return False
    wanted = normalized_label(goal["value"])
    return any(normalized_label(tag) == wanted for tag in mission_tags)


def observe_context_signal(
    path: Path,
    *,
    mission_id: str,
    mission_tags: list[str],
    signal: str,
) -> dict[str, Any] | None:
    """Update revisable first-run hypotheses from one meaningful product interaction."""
    context = load_onboarding_context(path)
    if context is None:
        return None

    signal_key = signal.strip().casefold()
    if signal_key not in _SIGNAL_DELTAS:
        allowed = ", ".join(sorted(_SIGNAL_DELTAS))
        raise ValueError(f"context signal must be one of: {allowed}")

    learning = _learning(context)
    learning["events"] += 1
    learning["last_mission_id"] = mission_id
    learning["last_signal"] = signal_key

    if _matches_primary_goal(context, mission_tags):
        goal = _hypothesis(context, "primary_goal")
        assert goal is not None
        delta = _SIGNAL_DELTAS[signal_key]
        if signal_key in {"more_like_this", "mission_completed"}:
            learning["primary_goal_support"] += 1
            learning["primary_goal_deferrals"] = max(
                0, learning["primary_goal_deferrals"] - 1
            )
        elif signal_key == "less_like_this":
            learning["primary_goal_conflict"] += 1
        elif signal_key == "not_now":
            learning["primary_goal_deferrals"] += 1

        if delta:
            goal["confidence"] = _clamp_confidence(float(goal["confidence"]) + delta)
            goal["source"] = "first_run_plus_behavior"

    _recompute_average(context)
    save_onboarding_context(path, context)
    return context


def clarification_for_context(
    context: dict[str, Any] | None,
    *,
    locale: str | None = None,
) -> dict[str, Any] | None:
    """Return at most one low-friction question when behavior contradicts the current model."""
    if not context:
        return None
    learning = context.get("learning")
    if not isinstance(learning, dict):
        return None
    if learning.get("events", 0) < learning.get("snooze_until_event", 0):
        return None

    resolved_locale = (
        locale_from_context(context)
        if locale is None
        else normalize_locale(locale)
    )
    russian = is_russian(resolved_locale)
    goal = _hypothesis(context, "primary_goal")
    if goal is None or not isinstance(goal.get("value"), str):
        return None
    label = goal["value"]
    confidence = float(goal.get("confidence", 0.0))

    if learning.get("primary_goal_conflict", 0) >= 2 and confidence <= 0.62:
        return {
            "id": "primary_goal_fit",
            "kind": "direction",
            "prompt": (
                f"Вы несколько раз уходили от задач, связанных с «{label}». Это всё ещё направление, которое Lumen стоит ставить в приоритет?"
                if russian
                else (
                    f"You’ve been steering away from work tied to “{label}”. "
                    "Is this still a direction you want Lumen to prioritize?"
                )
            ),
            "options": (
                [
                    {"choice": "keep_goal", "label": "Да, оставить"},
                    {"choice": "pause_goal", "label": "Не сейчас"},
                    {"choice": "not_sure", "label": "Не уверен"},
                ]
                if russian
                else [
                    {"choice": "keep_goal", "label": "Yes, keep it"},
                    {"choice": "pause_goal", "label": "Not right now"},
                    {"choice": "not_sure", "label": "I’m not sure"},
                ]
            ),
        }

    if learning.get("primary_goal_deferrals", 0) >= 3:
        return {
            "id": "repeated_deferral",
            "kind": "fit",
            "prompt": (
                f"Задачи по направлению «{label}» постоянно откладываются. Что сделает Lumen полезнее?"
                if russian
                else (
                    f"Work toward “{label}” keeps getting postponed. "
                    "What would make Lumen more useful here?"
                )
            ),
            "options": (
                [
                    {"choice": "make_smaller", "label": "Давай мельче"},
                    {"choice": "bad_timing", "label": "Сейчас плохой момент"},
                    {"choice": "not_useful", "label": "Эти задачи не полезны"},
                ]
                if russian
                else [
                    {"choice": "make_smaller", "label": "Give me smaller steps"},
                    {"choice": "bad_timing", "label": "The timing is bad"},
                    {"choice": "not_useful", "label": "This work isn’t useful"},
                ]
            ),
        }

    return None


def _next_smaller_focus(current: int) -> int:
    ordered = sorted(ALLOWED_FOCUS_MINUTES)
    smaller = [value for value in ordered if value < current]
    return smaller[-1] if smaller else ordered[0]


def answer_context_clarification(
    path: Path,
    *,
    clarification_id: str,
    choice: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply an answer and return `(context, effects)` for the application bridge."""
    context = load_onboarding_context(path)
    if context is None:
        raise ValueError("context clarification requires conversational onboarding state")
    active = clarification_for_context(context)
    if active is None or active["id"] != clarification_id:
        raise ValueError("context clarification is no longer active")

    choice_key = choice.strip().casefold()
    allowed = {item["choice"] for item in active["options"]}
    if choice_key not in allowed:
        raise ValueError(f"clarification choice must be one of: {', '.join(sorted(allowed))}")

    learning = _learning(context)
    goal = _hypothesis(context, "primary_goal")
    effects: dict[str, Any] = {}

    if clarification_id == "primary_goal_fit":
        assert goal is not None
        if choice_key == "keep_goal":
            goal["confidence"] = _clamp_confidence(max(float(goal["confidence"]), 0.76))
            goal["source"] = "confirmed_by_user"
            effects["confirm_goal"] = goal["value"]
        elif choice_key == "pause_goal":
            goal["confidence"] = _clamp_confidence(float(goal["confidence"]) - 0.12)
            goal["source"] = "deprioritized_by_user"
            effects["deprioritize_goal"] = goal["value"]
        learning["primary_goal_conflict"] = 0

    elif clarification_id == "repeated_deferral":
        if choice_key == "make_smaller":
            answers = context.get("answers", {})
            current = int(answers.get("focus_minutes", 30)) if isinstance(answers, dict) else 30
            focus_minutes = _next_smaller_focus(current)
            if isinstance(answers, dict):
                answers["focus_minutes"] = focus_minutes
            focus = _hypothesis(context, "focus_window")
            if focus is not None:
                focus["value"] = (
                    f"{focus_minutes} минут"
                    if is_russian(locale_from_context(context))
                    else f"{focus_minutes} minutes"
                )
                focus["confidence"] = 0.98
                focus["source"] = "adjusted_by_user"
            effects["focus_minutes"] = focus_minutes
        elif choice_key == "not_useful":
            effects["dislike_mission_id"] = learning.get("last_mission_id")
        learning["primary_goal_deferrals"] = 0

    learning["snooze_until_event"] = learning["events"] + 4
    learning["last_clarification"] = {
        "id": clarification_id,
        "choice": choice_key,
    }
    _recompute_average(context)
    save_onboarding_context(path, context)
    return context, effects
