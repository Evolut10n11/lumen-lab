from __future__ import annotations

import copy
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from .github_context_missions import reconcile_github_context_mission
from .github_user_context import load_github_snapshot
from .onboarding import (
    ALLOWED_FOCUS_MINUTES,
    ONBOARDING_CONTEXT_VERSION,
    apply_focus_minutes,
    goal_label,
    load_onboarding_context,
    save_onboarding_context,
)
from .personalization import build_profile, initialize_workspace
from .profile import Profile, load_profile, normalized_label
from .workspace import UserWorkspace


def _clean_text(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        raise ValueError(f"{name} must be a non-empty string")
    if len(cleaned) > 1200:
        raise ValueError(f"{name} must be 1200 characters or fewer")
    return cleaned


def _optional_text(value: str | None, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string or null")
    cleaned = " ".join(value.strip().split())
    if len(cleaned) > 1200:
        raise ValueError(f"{name} must be 1200 characters or fewer")
    return cleaned


def _primary_priority(profile: Profile) -> tuple[str, int]:
    if not profile.priorities:
        raise ValueError("profile must contain at least one priority")
    return sorted(
        profile.priorities.items(),
        key=lambda item: (-item[1], normalized_label(item[0])),
    )[0]


def _revised_priorities(profile: Profile, new_goal: str) -> dict[str, int]:
    old_primary, _ = _primary_priority(profile)
    old_key = normalized_label(old_primary)
    new_key = normalized_label(new_goal)
    result: dict[str, int] = {new_goal: 10}
    for name, weight in profile.priorities.items():
        key = normalized_label(name)
        if key in {old_key, new_key}:
            continue
        result[name] = min(weight, 8)
    return result


def _validated_focus_minutes(value: int | None, fallback: int) -> int:
    chosen = fallback if value is None else value
    if isinstance(chosen, bool) or chosen not in ALLOWED_FOCUS_MINUTES:
        allowed = ", ".join(str(item) for item in ALLOWED_FOCUS_MINUTES)
        raise ValueError(f"focus_minutes must be one of: {allowed}")
    return int(chosen)


def _answer_text(context: dict[str, Any] | None, key: str) -> str | None:
    if not context:
        return None
    answers = context.get("answers")
    if not isinstance(answers, dict):
        return None
    value = answers.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _replace_inferred_label(
    values: Iterable[str],
    *,
    old_value: str | None,
    new_value: str | None,
    exclude: str | None = None,
) -> tuple[str, ...]:
    old_key = normalized_label(old_value) if old_value else None
    exclude_key = normalized_label(exclude) if exclude else None
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = raw.strip()
        key = normalized_label(value)
        if old_key is not None and key == old_key:
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    if new_value:
        new_key = normalized_label(new_value)
        if new_key != exclude_key and new_key not in seen:
            result.insert(0, new_value)
    return tuple(result)


def _hypotheses(context: dict[str, Any]) -> list[dict[str, Any]]:
    raw = context.get("hypotheses")
    if not isinstance(raw, list):
        raw = []
        context["hypotheses"] = raw
    result = [item for item in raw if isinstance(item, dict)]
    if len(result) != len(raw):
        context["hypotheses"] = result
    return result


def _set_hypothesis(
    context: dict[str, Any],
    *,
    key: str,
    label: str,
    value: str,
    confidence: float,
    source: str,
) -> None:
    hypotheses = _hypotheses(context)
    for item in hypotheses:
        if item.get("key") == key:
            item.update(
                {
                    "label": label,
                    "value": value,
                    "confidence": confidence,
                    "source": source,
                }
            )
            return
    hypotheses.append(
        {
            "key": key,
            "label": label,
            "value": value,
            "confidence": confidence,
            "source": source,
        }
    )


def _remove_hypothesis(context: dict[str, Any], key: str) -> None:
    context["hypotheses"] = [
        item for item in _hypotheses(context) if item.get("key") != key
    ]


def _average_confidence(context: dict[str, Any]) -> float:
    values = [
        float(item["confidence"])
        for item in _hypotheses(context)
        if isinstance(item.get("confidence"), (int, float))
    ]
    return round(sum(values) / len(values), 2) if values else 0.0


def _existing_focus_minutes(context: dict[str, Any] | None) -> int:
    if not context:
        return 30
    answers = context.get("answers")
    if isinstance(answers, dict):
        value = answers.get("focus_minutes")
        if isinstance(value, int) and not isinstance(value, bool) and value in ALLOWED_FOCUS_MINUTES:
            return value
    return 30


def _revision_context(
    existing: dict[str, Any] | None,
    *,
    old_goal: str,
    desired_change: str,
    new_goal: str,
    current_context: str | None,
    friction: str | None,
    focus_minutes: int,
) -> dict[str, Any]:
    context = (
        copy.deepcopy(existing)
        if existing is not None
        else {
            "version": ONBOARDING_CONTEXT_VERSION,
            "source": "revision",
            "answers": {},
            "hypotheses": [],
        }
    )
    context["version"] = ONBOARDING_CONTEXT_VERSION

    answers = context.get("answers")
    if not isinstance(answers, dict):
        answers = {}
        context["answers"] = answers
    answers["desired_change"] = desired_change
    answers["focus_minutes"] = focus_minutes

    _set_hypothesis(
        context,
        key="primary_goal",
        label="What you want to change",
        value=new_goal,
        confidence=0.99,
        source="explicit_revision",
    )
    _set_hypothesis(
        context,
        key="focus_window",
        label="Realistic focus window",
        value=f"{focus_minutes} minutes",
        confidence=0.98,
        source="explicit_revision",
    )

    if current_context is not None:
        answers["current_context"] = current_context or None
        if current_context:
            _set_hypothesis(
                context,
                key="current_context",
                label="What has your attention now",
                value=current_context,
                confidence=0.96,
                source="explicit_revision",
            )
        else:
            _remove_hypothesis(context, "current_context")

    if friction is not None:
        answers["friction"] = friction or None
        if friction:
            _set_hypothesis(
                context,
                key="friction",
                label="What tends to get in the way",
                value=friction,
                confidence=0.94,
                source="explicit_revision",
            )
        else:
            _remove_hypothesis(context, "friction")

    revisions = context.get("revisions")
    if not isinstance(revisions, list):
        revisions = []
        context["revisions"] = revisions
    revisions.append(
        {
            "at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "kind": "primary_goal",
            "from": old_goal,
            "to": new_goal,
            "source": "user",
        }
    )

    learning = context.get("learning")
    if not isinstance(learning, dict):
        learning = {}
        context["learning"] = learning
    events = learning.get("events", 0)
    events = events if isinstance(events, int) and not isinstance(events, bool) else 0
    learning["primary_goal_support"] = 0
    learning["primary_goal_conflict"] = 0
    learning["primary_goal_deferrals"] = 0
    learning["snooze_until_event"] = events + 4
    learning["last_revision"] = {
        "from": old_goal,
        "to": new_goal,
    }

    context["average_confidence"] = _average_confidence(context)
    return context


def revise_user_direction(
    workspace: UserWorkspace,
    *,
    desired_change: str,
    current_context: str | None = None,
    friction: str | None = None,
    focus_minutes: int | None = None,
) -> dict[str, Any]:
    """Apply an explicit direction change and rebuild only current recommendation state."""
    workspace.require_initialized()
    profile = load_profile(workspace.profile_path)
    existing_context = load_onboarding_context(workspace.onboarding_context_path)

    desired_change = _clean_text(desired_change, "desired_change")
    current_context = _optional_text(current_context, "current_context")
    friction = _optional_text(friction, "friction")
    new_goal = goal_label(desired_change)
    old_goal, _ = _primary_priority(profile)
    chosen_focus = _validated_focus_minutes(
        focus_minutes,
        _existing_focus_minutes(existing_context),
    )

    previous_context = _answer_text(existing_context, "current_context")
    previous_friction = _answer_text(existing_context, "friction")
    interests = profile.interests
    constraints = profile.constraints
    if current_context is not None:
        interests = _replace_inferred_label(
            interests,
            old_value=previous_context,
            new_value=current_context or None,
            exclude=new_goal,
        )
    if friction is not None:
        constraints = _replace_inferred_label(
            constraints,
            old_value=previous_friction,
            new_value=friction or None,
        )

    revised_profile = build_profile(
        user_id=profile.id,
        display_name=profile.display_name,
        priorities=_revised_priorities(profile, new_goal),
        skills=profile.skills,
        interests=interests,
        constraints=constraints,
        preferred_stack=profile.preferred_stack,
        risk_tolerance=profile.risk_tolerance,
        policy_mode=profile.candidate_generation_policy.mode,
        allow_llm=profile.candidate_generation_policy.allow_llm,
        max_candidates=profile.candidate_generation_policy.max_candidates,
    )

    context = _revision_context(
        existing_context,
        old_goal=old_goal,
        desired_change=desired_change,
        new_goal=new_goal,
        current_context=current_context,
        friction=friction,
        focus_minutes=chosen_focus,
    )

    initialize_workspace(workspace, revised_profile, replace=True)
    apply_focus_minutes(workspace.work_sessions_path, chosen_focus)
    save_onboarding_context(workspace.onboarding_context_path, context)

    github_snapshot = load_github_snapshot(workspace.github_context_path)
    github_mission = None
    if github_snapshot is not None:
        github_mission = reconcile_github_context_mission(workspace, github_snapshot)

    return {
        "old_goal": old_goal,
        "new_goal": new_goal,
        "focus_minutes": chosen_focus,
        "reset_current_progress": True,
        "github_mission_id": None if github_mission is None else github_mission.id,
    }
