from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .feedback import PreferenceFeedback, feedback_adjustment, load_feedback, record_feedback
from .mission_radar import Mission, load_missions, radar_snapshot
from .personalization import build_profile, initialize_workspace, profile_payload
from .profile import Profile, load_profile, normalized_label
from .work_session import (
    choose_mission,
    load_progress,
    load_templates,
    mark_step_done,
    session_snapshot,
    template_for,
)
from .workspace import UserWorkspace

APP_SCHEMA_VERSION = 3


def _matched_priorities(mission: Mission, profile: Profile) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    mission_tags = {normalized_label(tag) for tag in mission.tags}
    for name, weight in profile.priorities.items():
        if normalized_label(name) in mission_tags:
            matches.append({"name": name, "weight": weight})
    return sorted(matches, key=lambda item: (-item["weight"], normalized_label(item["name"])))


def _quick_priorities(goals: Iterable[str]) -> dict[str, int]:
    clean: list[str] = []
    seen: set[str] = set()
    for raw in goals:
        value = raw.strip()
        key = normalized_label(value)
        if not value or key in seen:
            continue
        seen.add(key)
        clean.append(value)

    if not clean:
        raise ValueError("quick onboarding needs at least one goal")
    if len(clean) > 5:
        raise ValueError("quick onboarding supports at most five goals")

    weights = (10, 8, 7, 6, 5)
    return {goal: weights[index] for index, goal in enumerate(clean)}


def _selection_explanation(
    mission: Mission,
    profile: Profile,
    score: float,
    feedback: PreferenceFeedback,
) -> dict[str, Any]:
    matched = _matched_priorities(mission, profile)
    feedback_delta = feedback_adjustment(mission.id, mission.tags, feedback)
    reasons: list[str] = [mission.why_now]
    if matched:
        strongest = matched[0]
        reasons.append(
            f"It matches your priority '{strongest['name']}' weighted "
            f"{strongest['weight']}/10."
        )
    if mission.risk > profile.risk_tolerance:
        reasons.append(
            f"Its risk {mission.risk}/10 is above your tolerance "
            f"{profile.risk_tolerance}/10, so its personalized score is reduced."
        )
    else:
        reasons.append(
            f"Its risk {mission.risk}/10 is within your tolerance "
            f"{profile.risk_tolerance}/10."
        )
    if feedback_delta > 0:
        reasons.append("Your recent choices make this kind of work a better fit.")
    elif feedback_delta < 0:
        reasons.append("Your recent choices make this kind of work a weaker fit.")
    return {
        "score": score,
        "base_score": mission.score,
        "feedback_adjustment": feedback_delta,
        "matched_priorities": matched,
        "reasons": reasons,
    }


def _experience_payload(
    profile: Profile,
    today: dict[str, Any] | None,
    feedback: PreferenceFeedback,
) -> dict[str, Any]:
    if today is None:
        return {
            "headline": "You're clear for now.",
            "message": "There is no active mission competing for your attention.",
            "primary_action": None,
            "quick_actions": [],
            "learning": {
                "active": feedback.events > 0,
                "signal_count": feedback.events,
                "message": "Lumen adapts quietly as you use it.",
            },
        }

    progress = today.get("progress")
    completed = progress.get("completed", 0) if isinstance(progress, dict) else 0
    total = progress.get("total", 0) if isinstance(progress, dict) else 0
    primary_label = "Continue" if completed else "Start"

    return {
        "headline": f"One useful thing, {profile.display_name}.",
        "message": today["title"],
        "primary_action": {
            "action": "continue",
            "label": primary_label,
            "mission_id": today["mission_id"],
            "progress_label": f"{completed}/{total}" if total else None,
        },
        "quick_actions": [
            {
                "action": "more_like_this",
                "label": "More like this",
                "mission_id": today["mission_id"],
            },
            {
                "action": "not_now",
                "label": "Not now",
                "mission_id": today["mission_id"],
            },
            {
                "action": "less_like_this",
                "label": "Less like this",
                "mission_id": today["mission_id"],
            },
        ],
        "learning": {
            "active": feedback.events > 0,
            "signal_count": feedback.events,
            "message": (
                "Lumen is already adapting to what you actually do."
                if feedback.events
                else "No tuning required — your choices will personalize Lumen over time."
            ),
        },
    }


def _onboarding_payload() -> dict[str, Any]:
    return {
        "mode": "quick",
        "headline": "What do you want to move forward?",
        "message": "Give Lumen one to five goals. You can refine the rest later.",
        "fields": [
            {
                "name": "display_name",
                "kind": "text",
                "label": "What should Lumen call you?",
                "required": True,
            },
            {
                "name": "goals",
                "kind": "list",
                "label": "What matters most right now?",
                "required": True,
                "min_items": 1,
                "max_items": 5,
            },
        ],
        "submit_label": "Start with Lumen",
    }


@dataclass(slots=True)
class LumenApplication:
    """User-scoped application facade shared by CLI, API, and future GUI clients."""

    root: Path

    def onboard(
        self,
        user_id: str,
        *,
        display_name: str,
        priorities: dict[str, int],
        skills: Iterable[str] = (),
        interests: Iterable[str] = (),
        constraints: Iterable[str] = (),
        preferred_stack: Iterable[str] = (),
        risk_tolerance: int = 5,
        replace: bool = False,
    ) -> dict[str, Any]:
        """Create one isolated user workspace and return its first dashboard."""
        workspace = UserWorkspace.from_root(self.root, user_id)
        profile = build_profile(
            user_id=workspace.user_id,
            display_name=display_name,
            priorities=priorities,
            skills=skills,
            interests=interests,
            constraints=constraints,
            preferred_stack=preferred_stack,
            risk_tolerance=risk_tolerance,
        )
        initialize_workspace(workspace, profile, replace=replace)
        return self.dashboard(workspace.user_id)

    def quick_onboard(
        self,
        user_id: str,
        *,
        display_name: str,
        goals: Iterable[str],
        replace: bool = False,
    ) -> dict[str, Any]:
        """Create a useful profile from normal-language goals without tuning weights."""
        return self.onboard(
            user_id,
            display_name=display_name,
            priorities=_quick_priorities(goals),
            replace=replace,
        )

    def _users(self) -> list[dict[str, str]]:
        users_root = self.root / ".lumen" / "users"
        if not users_root.is_dir():
            return []

        users: list[dict[str, str]] = []
        for directory in sorted(users_root.iterdir(), key=lambda item: item.name.casefold()):
            profile_path = directory / "profile.json"
            if not directory.is_dir() or not profile_path.is_file():
                continue
            profile = load_profile(profile_path)
            users.append({"id": profile.id, "display_name": profile.display_name})
        return users

    def bootstrap(
        self,
        user_id: str | None = None,
        *,
        top: int = 3,
    ) -> dict[str, Any]:
        """Return everything a GUI needs to choose onboarding or the main dashboard."""
        workspace = UserWorkspace.from_root(self.root, user_id)
        initialized = workspace.initialized()
        return {
            "schema_version": APP_SCHEMA_VERSION,
            "selected_user_id": workspace.user_id,
            "initialized": initialized,
            "users": self._users(),
            "onboarding": None if initialized else _onboarding_payload(),
            "dashboard": self.dashboard(workspace.user_id, top=top) if initialized else None,
        }

    def workspace(self, user_id: str | None = None) -> UserWorkspace:
        workspace = UserWorkspace.from_root(self.root, user_id)
        workspace.require_initialized()
        return workspace

    def dashboard(self, user_id: str | None = None, *, top: int = 3) -> dict[str, Any]:
        workspace = self.workspace(user_id)
        profile = load_profile(workspace.profile_path)
        missions = load_missions(workspace.missions_path)
        feedback = load_feedback(workspace.feedback_path)
        radar = radar_snapshot(missions, top=top, profile=profile, feedback=feedback)
        templates = load_templates(workspace.work_sessions_path)
        progress = load_progress(workspace.work_progress_path)

        active_missions = [mission for mission in missions if mission.status == "active"]
        today: dict[str, Any] | None = None
        if active_missions:
            mission = choose_mission(missions, profile=profile, feedback=feedback)
            template = template_for(templates, mission.id)
            today = session_snapshot(mission, template, progress, profile, feedback)
            today["selection"] = _selection_explanation(
                mission,
                profile,
                float(today["score"]),
                feedback,
            )

        completed_steps = sum(len(items) for items in progress.values())
        total_steps = 0
        for template in templates:
            if any(mission.id == template.mission_id for mission in active_missions):
                total_steps += len(template.steps)

        return {
            "schema_version": APP_SCHEMA_VERSION,
            "user": profile_payload(profile),
            "experience": _experience_payload(profile, today, feedback),
            "today": today,
            "radar": radar,
            "personalization": {
                "adapting": feedback.events > 0,
                "signal_count": feedback.events,
            },
            "summary": {
                "active_missions": len(active_missions),
                "completed_steps": completed_steps,
                "total_active_steps": total_steps,
            },
        }

    def react_to_mission(
        self,
        action: str,
        user_id: str | None = None,
        *,
        mission_id: str | None = None,
        top: int = 3,
    ) -> dict[str, Any]:
        """Apply one low-friction preference action and return the refreshed dashboard."""
        actions = {
            "more_like_this": ("like", True),
            "not_now": ("dislike", False),
            "less_like_this": ("dislike", True),
        }
        action_key = action.strip().casefold()
        try:
            sentiment, include_tags = actions[action_key]
        except KeyError as exc:
            allowed = ", ".join(sorted(actions))
            raise ValueError(f"mission action must be one of: {allowed}") from exc

        workspace = self.workspace(user_id)
        profile = load_profile(workspace.profile_path)
        missions = load_missions(workspace.missions_path)
        feedback = load_feedback(workspace.feedback_path)
        mission = choose_mission(
            missions,
            mission_id=mission_id,
            profile=profile,
            feedback=feedback,
        )
        record_feedback(
            workspace.feedback_path,
            mission_id=mission.id,
            tags=mission.tags,
            sentiment=sentiment,
            include_tags=include_tags,
        )
        return self.dashboard(workspace.user_id, top=top)

    def rate_mission(
        self,
        sentiment: str,
        user_id: str | None = None,
        *,
        mission_id: str | None = None,
        top: int = 3,
    ) -> dict[str, Any]:
        """Compatibility API for explicit like/dislike feedback."""
        mapping = {"like": "more_like_this", "dislike": "less_like_this"}
        key = sentiment.strip().casefold()
        try:
            action = mapping[key]
        except KeyError as exc:
            raise ValueError("feedback sentiment must be one of: dislike, like") from exc
        return self.react_to_mission(
            action,
            user_id,
            mission_id=mission_id,
            top=top,
        )

    def complete_step(
        self,
        step_number: int,
        user_id: str | None = None,
        *,
        mission_id: str | None = None,
    ) -> dict[str, Any]:
        workspace = self.workspace(user_id)
        profile = load_profile(workspace.profile_path)
        missions = load_missions(workspace.missions_path)
        feedback = load_feedback(workspace.feedback_path)
        templates = load_templates(workspace.work_sessions_path)
        mission = choose_mission(
            missions,
            mission_id=mission_id,
            profile=profile,
            feedback=feedback,
        )
        template = template_for(templates, mission.id)
        before = load_progress(workspace.work_progress_path)
        was_complete = len(before.get(mission.id, [])) == len(template.steps)
        progress = mark_step_done(
            workspace.work_progress_path,
            mission.id,
            step_number,
            len(template.steps),
        )
        is_complete = len(progress.get(mission.id, [])) == len(template.steps)
        if is_complete and not was_complete:
            feedback = record_feedback(
                workspace.feedback_path,
                mission_id=mission.id,
                tags=mission.tags,
                sentiment="like",
            )
        snapshot = session_snapshot(mission, template, progress, profile, feedback)
        snapshot["selection"] = _selection_explanation(
            mission,
            profile,
            float(snapshot["score"]),
            feedback,
        )
        return snapshot
