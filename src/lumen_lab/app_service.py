from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .feedback import feedback_adjustment, load_feedback, record_feedback
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

APP_SCHEMA_VERSION = 2


def _matched_priorities(mission: Mission, profile: Profile) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    mission_tags = {normalized_label(tag) for tag in mission.tags}
    for name, weight in profile.priorities.items():
        if normalized_label(name) in mission_tags:
            matches.append({"name": name, "weight": weight})
    return sorted(matches, key=lambda item: (-item["weight"], normalized_label(item["name"])))


def _selection_explanation(
    mission: Mission,
    profile: Profile,
    score: float,
    feedback,
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
        reasons.append(
            f"Your previous feedback raises this mission by {feedback_delta:.2f} points."
        )
    elif feedback_delta < 0:
        reasons.append(
            f"Your previous feedback lowers this mission by {abs(feedback_delta):.2f} points."
        )
    return {
        "score": score,
        "base_score": mission.score,
        "feedback_adjustment": feedback_delta,
        "matched_priorities": matched,
        "reasons": reasons,
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
            "today": today,
            "radar": radar,
            "feedback": feedback.to_dict(),
            "summary": {
                "active_missions": len(active_missions),
                "completed_steps": completed_steps,
                "total_active_steps": total_steps,
                "feedback_events": feedback.events,
            },
        }

    def rate_mission(
        self,
        sentiment: str,
        user_id: str | None = None,
        *,
        mission_id: str | None = None,
        top: int = 3,
    ) -> dict[str, Any]:
        """Record explicit user preference feedback and return the updated dashboard."""
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
        )
        return self.dashboard(workspace.user_id, top=top)

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
        progress = mark_step_done(
            workspace.work_progress_path,
            mission.id,
            step_number,
            len(template.steps),
        )
        snapshot = session_snapshot(mission, template, progress, profile, feedback)
        snapshot["selection"] = _selection_explanation(
            mission,
            profile,
            float(snapshot["score"]),
            feedback,
        )
        return snapshot
