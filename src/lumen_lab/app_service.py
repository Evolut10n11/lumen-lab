from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mission_radar import Mission, load_missions, radar_snapshot
from .personalization import profile_payload
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


def _matched_priorities(mission: Mission, profile: Profile) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    mission_tags = {normalized_label(tag) for tag in mission.tags}
    for name, weight in profile.priorities.items():
        if normalized_label(name) in mission_tags:
            matches.append({"name": name, "weight": weight})
    return sorted(matches, key=lambda item: (-item["weight"], normalized_label(item["name"])))


def _selection_explanation(mission: Mission, profile: Profile, score: float) -> dict[str, Any]:
    matched = _matched_priorities(mission, profile)
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
    return {
        "score": score,
        "base_score": mission.score,
        "matched_priorities": matched,
        "reasons": reasons,
    }


@dataclass(slots=True)
class LumenApplication:
    """User-scoped application facade shared by CLI, API, and future GUI clients."""

    root: Path

    def workspace(self, user_id: str | None = None) -> UserWorkspace:
        workspace = UserWorkspace.from_root(self.root, user_id)
        workspace.require_initialized()
        return workspace

    def dashboard(self, user_id: str | None = None, *, top: int = 3) -> dict[str, Any]:
        workspace = self.workspace(user_id)
        profile = load_profile(workspace.profile_path)
        missions = load_missions(workspace.missions_path)
        radar = radar_snapshot(missions, top=top, profile=profile)
        templates = load_templates(workspace.work_sessions_path)
        progress = load_progress(workspace.work_progress_path)

        active_missions = [mission for mission in missions if mission.status == "active"]
        today: dict[str, Any] | None = None
        if active_missions:
            mission = choose_mission(missions, profile=profile)
            template = template_for(templates, mission.id)
            today = session_snapshot(mission, template, progress, profile)
            today["selection"] = _selection_explanation(
                mission,
                profile,
                float(today["score"]),
            )

        completed_steps = sum(len(items) for items in progress.values())
        total_steps = 0
        for template in templates:
            if any(mission.id == template.mission_id for mission in active_missions):
                total_steps += len(template.steps)

        return {
            "user": profile_payload(profile),
            "today": today,
            "radar": radar,
            "summary": {
                "active_missions": len(active_missions),
                "completed_steps": completed_steps,
                "total_active_steps": total_steps,
            },
        }

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
        templates = load_templates(workspace.work_sessions_path)
        mission = choose_mission(missions, mission_id=mission_id, profile=profile)
        template = template_for(templates, mission.id)
        progress = mark_step_done(
            workspace.work_progress_path,
            mission.id,
            step_number,
            len(template.steps),
        )
        snapshot = session_snapshot(mission, template, progress, profile)
        snapshot["selection"] = _selection_explanation(
            mission,
            profile,
            float(snapshot["score"]),
        )
        return snapshot
