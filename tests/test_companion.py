from __future__ import annotations

from pathlib import Path

from lumen_lab.app_service import LumenApplication
from lumen_lab.companion import MISSION_XP, STEP_XP, load_companion_state
from lumen_lab.context_revision import revise_user_direction
from lumen_lab.workspace import UserWorkspace


def _app_with_user(tmp_path: Path, user_id: str = "alice") -> LumenApplication:
    app = LumenApplication(tmp_path)
    app.onboard(user_id, display_name=user_id.title(), priorities={"career": 10})
    return app


def test_dashboard_includes_three_free_companions(tmp_path: Path) -> None:
    dashboard = _app_with_user(tmp_path).dashboard("alice")

    assert [item["id"] for item in dashboard["companion"]["characters"]] == [
        "lumi",
        "kiro",
        "momo",
    ]
    assert {item["access"] for item in dashboard["companion"]["characters"]} == {
        "free"
    }
    assert dashboard["companion"]["selected"]["id"] == "lumi"
    assert dashboard["companion"]["level"] == 1
    assert dashboard["companion"]["total_xp"] == 0


def test_step_and_mission_events_award_xp_once(tmp_path: Path) -> None:
    app = _app_with_user(tmp_path)
    dashboard = app.dashboard("alice")
    mission_id = dashboard["today"]["mission_id"]
    step_count = dashboard["today"]["progress"]["total"]

    app.complete_step(1, "alice", mission_id=mission_id)
    first = app.dashboard("alice")
    assert first["companion"]["total_xp"] == STEP_XP
    assert first["companion"]["last_reaction"]["kind"] == "step_completed"

    app.complete_step(1, "alice", mission_id=mission_id)
    assert app.dashboard("alice")["companion"]["total_xp"] == STEP_XP

    for step in range(2, step_count + 1):
        app.complete_step(step, "alice", mission_id=mission_id)
    completed = app.dashboard("alice")

    assert completed["companion"]["total_xp"] == step_count * STEP_XP + MISSION_XP
    assert completed["companion"]["last_reaction"]["kind"] == "mission_completed"
    state = load_companion_state(
        UserWorkspace.from_root(tmp_path, "alice").companion_path
    )
    assert len(state.processed_event_ids) == step_count + 1


def test_companion_selection_persists_without_moving_xp_between_users(
    tmp_path: Path,
) -> None:
    app = _app_with_user(tmp_path)
    app.onboard("bob", display_name="Bob", priorities={"health": 10})
    mission_id = app.dashboard("alice")["today"]["mission_id"]
    app.complete_step(1, "alice", mission_id=mission_id)
    app.dashboard("alice")

    selected = app.select_companion("momo", "alice", locale="ru")

    assert selected["companion"]["selected"]["id"] == "momo"
    assert selected["companion"]["selected"]["name"] == "Момо"
    assert selected["companion"]["total_xp"] == STEP_XP
    assert app.dashboard("bob")["companion"]["selected"]["id"] == "lumi"
    assert app.dashboard("bob")["companion"]["total_xp"] == 0


def test_corrupt_companion_state_is_quarantined_independently(tmp_path: Path) -> None:
    app = _app_with_user(tmp_path)
    workspace = UserWorkspace.from_root(tmp_path, "alice")
    workspace.companion_path.write_text("{", encoding="utf-8")

    result = app.bootstrap("alice")

    assert result["initialized"] is True
    assert result["dashboard"]["companion"]["selected"]["id"] == "lumi"
    assert list(workspace.directory.glob("companion.corrupt-*.json"))


def test_new_direction_chapter_keeps_xp_and_can_reward_rebuilt_work(tmp_path: Path) -> None:
    app = _app_with_user(tmp_path)
    first = app.dashboard("alice")
    mission_id = first["today"]["mission_id"]
    app.complete_step(1, "alice", mission_id=mission_id)
    earned = app.dashboard("alice")["companion"]["total_xp"]
    workspace = UserWorkspace.from_root(tmp_path, "alice")

    revise_user_direction(workspace, desired_change="career", focus_minutes=30)
    rebuilt = app.dashboard("alice")
    assert rebuilt["companion"]["total_xp"] == earned

    rebuilt_id = rebuilt["today"]["mission_id"]
    app.complete_step(1, "alice", mission_id=rebuilt_id)

    assert app.dashboard("alice")["companion"]["total_xp"] == earned + STEP_XP


def test_replacing_workspace_starts_a_new_companion_chapter(tmp_path: Path) -> None:
    app = _app_with_user(tmp_path)
    first = app.dashboard("alice")
    mission_id = first["today"]["mission_id"]
    app.complete_step(1, "alice", mission_id=mission_id)
    earned = app.dashboard("alice")["companion"]["total_xp"]

    rebuilt = app.onboard(
        "alice",
        display_name="Alice",
        priorities={"career": 10},
        replace=True,
    )
    assert rebuilt["today"]["mission_id"] == mission_id
    assert rebuilt["companion"]["total_xp"] == earned

    app.complete_step(1, "alice", mission_id=mission_id)

    assert app.dashboard("alice")["companion"]["total_xp"] == earned + STEP_XP
