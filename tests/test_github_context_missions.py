from __future__ import annotations

import json

from lumen_lab.github_context_missions import (
    GITHUB_CONTEXT_MISSION_PREFIX,
    clear_github_context_missions,
    reconcile_github_context_mission,
)
from lumen_lab.mission_radar import load_missions
from lumen_lab.personalization import build_profile, initialize_workspace
from lumen_lab.work_session import load_templates, mark_step_done
from lumen_lab.workspace import UserWorkspace


def _workspace(tmp_path, *, user_id: str = "alice") -> UserWorkspace:
    workspace = UserWorkspace.from_root(tmp_path, user_id)
    profile = build_profile(
        user_id=user_id,
        display_name="Alice",
        priorities={"Ship portfolio evidence": 10, "Learn deeply": 7},
        skills=("Python",),
        interests=("AI",),
        risk_tolerance=4,
    )
    initialize_workspace(workspace, profile)
    return workspace


def _snapshot(project: str | None, language: str | None = "Python") -> dict[str, object]:
    return {
        "schema_version": 1,
        "source": "github_public",
        "signals": {
            "active_project": project,
            "primary_language": language,
        },
    }


def _derived_missions(workspace: UserWorkspace):
    return [
        mission
        for mission in load_missions(workspace.missions_path)
        if mission.id.startswith(GITHUB_CONTEXT_MISSION_PREFIX)
    ]


def test_reconcile_adds_profile_aligned_github_mission_and_session(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    before_count = len(load_missions(workspace.missions_path))

    mission = reconcile_github_context_mission(
        workspace,
        _snapshot("alice/lumen-lab", "Python"),
    )

    assert mission is not None
    assert mission.title == "Use lumen-lab to move Ship portfolio evidence forward"
    assert "Ship portfolio evidence" in mission.tags
    assert "alice/lumen-lab" in mission.tags
    assert "Python" in mission.tags
    assert len(load_missions(workspace.missions_path)) == before_count + 1

    templates = load_templates(workspace.work_sessions_path)
    template = next(item for item in templates if item.mission_id == mission.id)
    assert template.focus_minutes == 60
    assert "lumen-lab" in template.definition_of_done


def test_refresh_replaces_stale_github_mission_instead_of_accumulating(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    first = reconcile_github_context_mission(workspace, _snapshot("alice/old-project"))
    second = reconcile_github_context_mission(workspace, _snapshot("alice/new-project", "Rust"))

    assert first is not None and second is not None
    assert first.id != second.id
    derived = _derived_missions(workspace)
    assert [mission.id for mission in derived] == [second.id]
    assert "alice/new-project" in derived[0].tags
    assert "Rust" in derived[0].tags


def test_refresh_clears_progress_for_replaced_github_mission(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    first = reconcile_github_context_mission(workspace, _snapshot("alice/old-project"))
    assert first is not None
    template = next(
        item for item in load_templates(workspace.work_sessions_path) if item.mission_id == first.id
    )
    mark_step_done(workspace.work_progress_path, first.id, 1, len(template.steps))

    reconcile_github_context_mission(workspace, _snapshot("alice/new-project"))

    progress = json.loads(workspace.work_progress_path.read_text(encoding="utf-8"))
    assert first.id not in progress


def test_refresh_preserves_progress_when_project_and_priority_are_unchanged(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    first = reconcile_github_context_mission(workspace, _snapshot("alice/lumen-lab"))
    assert first is not None
    template = next(
        item for item in load_templates(workspace.work_sessions_path) if item.mission_id == first.id
    )
    mark_step_done(workspace.work_progress_path, first.id, 1, len(template.steps))

    refreshed = reconcile_github_context_mission(
        workspace,
        _snapshot("alice/lumen-lab", "Python"),
    )

    assert refreshed is not None
    assert refreshed.id == first.id
    progress = json.loads(workspace.work_progress_path.read_text(encoding="utf-8"))
    assert progress[first.id] == [1]


def test_disconnect_removes_only_github_derived_work(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    original_ids = [mission.id for mission in load_missions(workspace.missions_path)]
    mission = reconcile_github_context_mission(workspace, _snapshot("alice/lumen-lab"))
    assert mission is not None

    changed = clear_github_context_missions(workspace)

    assert changed is True
    assert [mission.id for mission in load_missions(workspace.missions_path)] == original_ids
    assert all(
        not template.mission_id.startswith(GITHUB_CONTEXT_MISSION_PREFIX)
        for template in load_templates(workspace.work_sessions_path)
    )


def test_missing_active_project_removes_existing_derived_mission(tmp_path) -> None:
    workspace = _workspace(tmp_path)
    reconcile_github_context_mission(workspace, _snapshot("alice/lumen-lab"))
    assert len(_derived_missions(workspace)) == 1

    mission = reconcile_github_context_mission(workspace, _snapshot(None, None))

    assert mission is None
    assert _derived_missions(workspace) == []
