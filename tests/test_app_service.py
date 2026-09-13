from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumen_lab.app_cli import main as dashboard_main
from lumen_lab.app_service import APP_SCHEMA_VERSION, LumenApplication
from lumen_lab.personalization import build_profile, initialize_workspace
from lumen_lab.workspace import UserWorkspace


def _initialize(root: Path, user_id: str, priority: str, interest: str) -> UserWorkspace:
    workspace = UserWorkspace.from_root(root, user_id)
    profile = build_profile(
        user_id=user_id,
        display_name=user_id.title(),
        priorities={priority: 10},
        interests=[interest],
        skills=["planning"],
        constraints=["4 hours per week"],
        risk_tolerance=4,
    )
    initialize_workspace(workspace, profile)
    return workspace


def test_bootstrap_routes_new_user_to_onboarding(tmp_path: Path) -> None:
    payload = LumenApplication(tmp_path).bootstrap("alice")

    assert payload["schema_version"] == APP_SCHEMA_VERSION
    assert payload["selected_user_id"] == "alice"
    assert payload["initialized"] is False
    assert payload["users"] == []
    assert payload["dashboard"] is None
    assert payload["onboarding"]["mode"] == "quick"
    assert payload["onboarding"]["submit_label"] == "Start with Lumen"
    assert [field["name"] for field in payload["onboarding"]["fields"]] == [
        "display_name",
        "goals",
    ]


def test_bootstrap_lists_users_and_embeds_selected_dashboard(tmp_path: Path) -> None:
    app = LumenApplication(tmp_path)
    app.onboard("alice", display_name="Alice", priorities={"career": 10})
    app.onboard("bob", display_name="Bob", priorities={"health": 10})

    payload = app.bootstrap("bob", top=2)

    assert payload["schema_version"] == APP_SCHEMA_VERSION
    assert payload["selected_user_id"] == "bob"
    assert payload["initialized"] is True
    assert payload["onboarding"] is None
    assert payload["users"] == [
        {"id": "alice", "display_name": "Alice"},
        {"id": "bob", "display_name": "Bob"},
    ]
    assert payload["dashboard"]["user"]["id"] == "bob"
    assert len(payload["dashboard"]["radar"]) == 2


def test_onboard_creates_first_personalized_dashboard(tmp_path: Path) -> None:
    app = LumenApplication(tmp_path)

    payload = app.onboard(
        "alice",
        display_name="Alice",
        priorities={"career": 10, "health": 7},
        interests=["robotics"],
        skills=["python"],
        constraints=["4 hours per week"],
        risk_tolerance=4,
    )

    assert payload["schema_version"] == APP_SCHEMA_VERSION
    assert payload["user"]["id"] == "alice"
    assert payload["user"]["priorities"] == {"career": 10, "health": 7}
    assert payload["today"]["profile_id"] == "alice"
    assert "career" in payload["today"]["title"].casefold()
    assert payload["summary"]["completed_steps"] == 0


def test_onboard_requires_explicit_replace_for_existing_user(tmp_path: Path) -> None:
    app = LumenApplication(tmp_path)
    app.onboard("alice", display_name="Alice", priorities={"career": 10})

    with pytest.raises(ValueError, match="already exists"):
        app.onboard("alice", display_name="Alice", priorities={"health": 10})


def test_onboard_replace_rebuilds_profile_and_resets_progress(tmp_path: Path) -> None:
    app = LumenApplication(tmp_path)
    app.onboard("alice", display_name="Alice", priorities={"career": 10})
    app.complete_step(1, "alice")

    payload = app.onboard(
        "alice",
        display_name="Alice",
        priorities={"health": 10},
        replace=True,
    )

    assert payload["user"]["priorities"] == {"health": 10}
    assert "health" in payload["today"]["title"].casefold()
    assert payload["summary"]["completed_steps"] == 0


def test_dashboard_is_scoped_to_selected_user(tmp_path: Path) -> None:
    _initialize(tmp_path, "alice", "career", "robotics")
    _initialize(tmp_path, "bob", "fitness", "running")
    app = LumenApplication(tmp_path)

    alice = app.dashboard("alice")
    bob = app.dashboard("bob")

    assert alice["schema_version"] == APP_SCHEMA_VERSION
    assert alice["user"]["id"] == "alice"
    assert bob["user"]["id"] == "bob"
    assert "career" in alice["today"]["title"].casefold()
    assert "fitness" in bob["today"]["title"].casefold()
    assert alice["today"]["mission_id"] != bob["today"]["mission_id"]


def test_dashboard_explains_why_top_mission_was_selected(tmp_path: Path) -> None:
    _initialize(tmp_path, "alice", "career", "robotics")
    payload = LumenApplication(tmp_path).dashboard("alice")

    selection = payload["today"]["selection"]
    assert selection["matched_priorities"] == [{"name": "career", "weight": 10}]
    assert any("career" in reason.casefold() for reason in selection["reasons"])
    assert selection["score"] >= selection["base_score"]


def test_completing_step_never_changes_another_user_progress(tmp_path: Path) -> None:
    _initialize(tmp_path, "alice", "career", "robotics")
    _initialize(tmp_path, "bob", "fitness", "running")
    app = LumenApplication(tmp_path)

    app.complete_step(1, "alice")
    alice = app.dashboard("alice")
    bob = app.dashboard("bob")

    assert alice["today"]["progress"]["completed"] == 1
    assert bob["today"]["progress"]["completed"] == 0
    assert alice["summary"]["completed_steps"] == 1
    assert bob["summary"]["completed_steps"] == 0


def test_dashboard_cli_emits_application_json(tmp_path: Path, capsys) -> None:
    _initialize(tmp_path, "alice", "career", "robotics")

    code = dashboard_main(
        ["--root", str(tmp_path), "--user", "alice", "--top", "2", "--json"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["schema_version"] == APP_SCHEMA_VERSION
    assert payload["user"]["id"] == "alice"
    assert len(payload["radar"]) == 2
    assert payload["today"]["profile_id"] == "alice"


def test_dashboard_cli_done_updates_only_selected_user(tmp_path: Path, capsys) -> None:
    _initialize(tmp_path, "alice", "career", "robotics")
    _initialize(tmp_path, "bob", "fitness", "running")

    assert dashboard_main(
        ["--root", str(tmp_path), "--user", "alice", "--done", "1", "--json"]
    ) == 0
    capsys.readouterr()

    bob = LumenApplication(tmp_path).dashboard("bob")
    assert bob["today"]["progress"]["completed"] == 0
