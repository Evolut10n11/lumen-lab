from __future__ import annotations

import hashlib
import json
from typing import Any

from .mission_radar import Mission, load_missions
from .profile import Profile, load_profile, normalized_label
from .work_session import WorkSessionTemplate, load_progress, load_templates
from .workspace import UserWorkspace

GITHUB_CONTEXT_MISSION_PREFIX = "github-context-"


def _primary_priority(profile: Profile) -> tuple[str, int] | None:
    if not profile.priorities:
        return None
    return sorted(
        profile.priorities.items(),
        key=lambda item: (-item[1], normalized_label(item[0])),
    )[0]


def _dedupe_tags(*values: str | None) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        if not isinstance(raw, str):
            continue
        value = raw.strip()
        if not value:
            continue
        key = normalized_label(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result)


def _github_signals(snapshot: dict[str, Any]) -> tuple[str | None, str | None]:
    signals = snapshot.get("signals")
    if not isinstance(signals, dict):
        return None, None
    active_project = signals.get("active_project")
    primary_language = signals.get("primary_language")
    project = active_project.strip() if isinstance(active_project, str) else None
    language = primary_language.strip() if isinstance(primary_language, str) else None
    return project or None, language or None


def github_context_mission(profile: Profile, snapshot: dict[str, Any]) -> Mission | None:
    """Build one low-risk mission from explicit priorities plus connected GitHub evidence."""
    priority = _primary_priority(profile)
    active_project, primary_language = _github_signals(snapshot)
    if priority is None or active_project is None:
        return None

    priority_name, priority_weight = priority
    project_name = active_project.rsplit("/", 1)[-1]
    digest_source = (
        f"{profile.id}:github:{active_project.casefold()}:"
        f"{normalized_label(priority_name)}"
    )
    digest = hashlib.sha256(digest_source.encode()).hexdigest()[:10]
    language_note = f" Its primary language is {primary_language}." if primary_language else ""

    mission = Mission(
        id=f"{GITHUB_CONTEXT_MISSION_PREFIX}{digest}",
        title=f"Use {project_name} to move {priority_name} forward",
        why_now=(
            f"Your connected GitHub shows {active_project} as your most active public "
            f"repository, while {priority_name} is your top Lumen priority at "
            f"{priority_weight}/10.{language_note}"
        ),
        next_action=(
            f"Choose one concrete change in {project_name} that creates visible evidence "
            f"for {priority_name}, define what done means, and complete the smallest "
            "bounded slice."
        ),
        impact=min(10, max(7, priority_weight)),
        urgency=min(10, max(5, priority_weight - 1)),
        leverage=9,
        momentum=9,
        effort=4,
        risk=max(1, min(3, profile.risk_tolerance)),
        status="active",
        tags=_dedupe_tags(
            priority_name,
            active_project,
            project_name,
            primary_language,
            "github",
        ),
    )
    mission.validate()
    return mission


def _github_work_session(
    mission: Mission,
    *,
    project_name: str,
    priority_name: str,
    focus_minutes: int,
) -> WorkSessionTemplate:
    template = WorkSessionTemplate(
        mission_id=mission.id,
        focus_minutes=focus_minutes,
        steps=(
            f"Open {project_name} and identify the single most useful unfinished change.",
            f"Write one sentence connecting that change to {priority_name}.",
            "Define a bounded deliverable that can be completed in this focus block.",
            "Implement or produce that deliverable without expanding the scope.",
            "Record the resulting artifact, what changed, and the next best action.",
        ),
        definition_of_done=(
            f"{project_name} contains one visible artifact or change that provides evidence "
            f"of progress toward {priority_name}, with the next action recorded."
        ),
    )
    template.validate()
    return template


def _write_missions(workspace: UserWorkspace, missions: list[Mission]) -> None:
    payload: list[dict[str, Any]] = []
    for mission in missions:
        item = mission.to_dict()
        item.pop("score", None)
        payload.append(item)
    workspace.missions_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_templates(workspace: UserWorkspace, templates: list[WorkSessionTemplate]) -> None:
    payload = [
        {
            "mission_id": template.mission_id,
            "focus_minutes": template.focus_minutes,
            "steps": list(template.steps),
            "definition_of_done": template.definition_of_done,
        }
        for template in templates
    ]
    workspace.work_sessions_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _clear_github_progress(
    workspace: UserWorkspace,
    *,
    keep_mission_id: str | None = None,
) -> None:
    if not workspace.work_progress_path.exists():
        return
    progress = load_progress(workspace.work_progress_path)
    filtered = {
        mission_id: completed
        for mission_id, completed in progress.items()
        if (
            not mission_id.startswith(GITHUB_CONTEXT_MISSION_PREFIX)
            or mission_id == keep_mission_id
        )
    }
    if filtered == progress:
        return
    workspace.work_progress_path.write_text(
        json.dumps(filtered, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def clear_github_context_missions(workspace: UserWorkspace) -> bool:
    """Remove only missions and sessions that were derived from connected GitHub evidence."""
    workspace.require_initialized()
    missions = load_missions(workspace.missions_path)
    templates = load_templates(workspace.work_sessions_path)
    filtered_missions = [
        mission
        for mission in missions
        if not mission.id.startswith(GITHUB_CONTEXT_MISSION_PREFIX)
    ]
    filtered_templates = [
        template
        for template in templates
        if not template.mission_id.startswith(GITHUB_CONTEXT_MISSION_PREFIX)
    ]
    changed = len(filtered_missions) != len(missions) or len(filtered_templates) != len(templates)
    if changed:
        _write_missions(workspace, filtered_missions)
        _write_templates(workspace, filtered_templates)
    _clear_github_progress(workspace)
    return changed


def reconcile_github_context_mission(
    workspace: UserWorkspace,
    snapshot: dict[str, Any],
) -> Mission | None:
    """Replace stale GitHub-derived work with one current, profile-aligned mission."""
    workspace.require_initialized()
    profile = load_profile(workspace.profile_path)
    missions = load_missions(workspace.missions_path)
    templates = load_templates(workspace.work_sessions_path)
    base_missions = [
        mission
        for mission in missions
        if not mission.id.startswith(GITHUB_CONTEXT_MISSION_PREFIX)
    ]
    base_templates = [
        template
        for template in templates
        if not template.mission_id.startswith(GITHUB_CONTEXT_MISSION_PREFIX)
    ]

    mission = github_context_mission(profile, snapshot)
    if mission is None:
        _clear_github_progress(workspace)
        _write_missions(workspace, base_missions)
        _write_templates(workspace, base_templates)
        return None

    existing_ids = {item.id for item in missions}
    keep_progress = mission.id if mission.id in existing_ids else None
    _clear_github_progress(workspace, keep_mission_id=keep_progress)

    priority = _primary_priority(profile)
    assert priority is not None
    active_project, _ = _github_signals(snapshot)
    assert active_project is not None
    project_name = active_project.rsplit("/", 1)[-1]
    focus_minutes = base_templates[0].focus_minutes if base_templates else 30
    template = _github_work_session(
        mission,
        project_name=project_name,
        priority_name=priority[0],
        focus_minutes=focus_minutes,
    )

    _write_missions(workspace, [*base_missions, mission])
    _write_templates(workspace, [*base_templates, template])
    return mission
