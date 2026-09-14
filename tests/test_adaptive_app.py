from __future__ import annotations

from pathlib import Path

from lumen_lab.app_service import LumenApplication
from lumen_lab.feedback import load_feedback
from lumen_lab.mission_radar import load_missions
from lumen_lab.workspace import UserWorkspace


def _app_with_user(tmp_path: Path, user_id: str = "alice") -> LumenApplication:
    app = LumenApplication(tmp_path)
    app.onboard(
        user_id,
        display_name=user_id.title(),
        priorities={"career": 10, "health": 7},
        interests=["robotics"],
        skills=["python"],
        risk_tolerance=4,
    )
    return app


def test_dashboard_exposes_product_actions_instead_of_tuning_controls(tmp_path: Path) -> None:
    app = _app_with_user(tmp_path)

    payload = app.dashboard("alice")
    experience = payload["experience"]

    assert experience["primary_action"]["label"] == "Start"
    assert [item["action"] for item in experience["quick_actions"]] == [
        "more_like_this",
        "not_now",
        "less_like_this",
    ]
    assert experience["learning"]["active"] is False
    assert "No tuning required" in experience["learning"]["message"]
    assert payload["personalization"] == {"adapting": False, "signal_count": 0}


def test_not_now_only_downranks_the_current_item(tmp_path: Path) -> None:
    app = _app_with_user(tmp_path)
    before = app.dashboard("alice")
    mission_id = before["today"]["mission_id"]

    after = app.react_to_mission("not_now", "alice", mission_id=mission_id)
    feedback = load_feedback(UserWorkspace.from_root(tmp_path, "alice").feedback_path)

    assert feedback.missions == {mission_id: -1}
    assert feedback.tags == {}
    assert after["personalization"] == {"adapting": True, "signal_count": 1}


def test_more_like_this_generalizes_to_the_kind_of_work(tmp_path: Path) -> None:
    app = _app_with_user(tmp_path)
    before = app.dashboard("alice")
    mission_id = before["today"]["mission_id"]

    app.react_to_mission("more_like_this", "alice", mission_id=mission_id)
    feedback = load_feedback(UserWorkspace.from_root(tmp_path, "alice").feedback_path)

    assert feedback.missions[mission_id] == 1
    assert feedback.tags
    assert all(value == 1 for value in feedback.tags.values())


def test_finishing_a_session_teaches_lumen_without_an_extra_rating(tmp_path: Path) -> None:
    app = _app_with_user(tmp_path)
    dashboard = app.dashboard("alice")
    mission_id = dashboard["today"]["mission_id"]
    step_count = dashboard["today"]["progress"]["total"]
    active_before = dashboard["summary"]["active_missions"]

    for step_number in range(1, step_count + 1):
        app.complete_step(step_number, "alice", mission_id=mission_id)

    adapted = app.dashboard("alice")
    assert adapted["personalization"] == {"adapting": True, "signal_count": 1}
    assert adapted["summary"]["active_missions"] == active_before - 1
    assert adapted["summary"]["completed_missions"] == 1
    assert adapted["summary"]["completed_steps"] == step_count
    assert adapted["summary"]["total_steps"] >= step_count
    assert adapted["summary"]["completed_active_steps"] == 0
    assert adapted["today"]["mission_id"] != mission_id
    workspace = UserWorkspace.from_root(tmp_path, "alice")
    completed = next(
        item for item in load_missions(workspace.missions_path) if item.id == mission_id
    )
    assert completed.status == "done"

    app.complete_step(step_count, "alice", mission_id=mission_id)
    repeated = app.dashboard("alice")
    assert repeated["personalization"]["signal_count"] == 1


def test_feedback_never_leaks_between_users(tmp_path: Path) -> None:
    app = _app_with_user(tmp_path, "alice")
    app.onboard("bob", display_name="Bob", priorities={"health": 10})
    mission_id = app.dashboard("alice")["today"]["mission_id"]

    app.react_to_mission("more_like_this", "alice", mission_id=mission_id)

    assert app.dashboard("alice")["personalization"]["signal_count"] == 1
    assert app.dashboard("bob")["personalization"]["signal_count"] == 0
