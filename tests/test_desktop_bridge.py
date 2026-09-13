from pathlib import Path

import pytest

from lumen_lab.desktop_bridge import dispatch


def request(root: Path, action: str, *, user_id: str = "default", **payload: object):
    return dispatch(
        {
            "root": str(root),
            "action": action,
            "user_id": user_id,
            "payload": payload,
        }
    )


def test_desktop_bootstrap_starts_in_onboarding(tmp_path: Path) -> None:
    payload = request(tmp_path, "bootstrap")

    assert payload["initialized"] is False
    assert payload["selected_user_id"] == "default"
    assert payload["onboarding"]["mode"] == "quick"


def test_desktop_quick_onboard_returns_product_dashboard(tmp_path: Path) -> None:
    dashboard = request(
        tmp_path,
        "quick_onboard",
        display_name="Alex",
        goals=["Build my AI career", "Ship a product"],
    )

    assert dashboard["user"]["display_name"] == "Alex"
    assert dashboard["experience"]["primary_action"]["action"] == "continue"
    assert dashboard["today"]["steps"]


def test_desktop_reaction_updates_only_selected_user(tmp_path: Path) -> None:
    request(tmp_path, "quick_onboard", display_name="Alex", goals=["Career"])
    request(
        tmp_path,
        "quick_onboard",
        user_id="bob",
        display_name="Bob",
        goals=["Fitness"],
    )

    alex_before = request(tmp_path, "dashboard")
    mission_id = alex_before["today"]["mission_id"]
    alex_after = request(
        tmp_path,
        "react",
        reaction="more_like_this",
        mission_id=mission_id,
    )
    bob = request(tmp_path, "dashboard", user_id="bob")

    assert alex_after["personalization"]["signal_count"] == 1
    assert bob["personalization"]["signal_count"] == 0


def test_desktop_complete_step_persists_progress(tmp_path: Path) -> None:
    dashboard = request(tmp_path, "quick_onboard", display_name="Alex", goals=["Career"])
    mission_id = dashboard["today"]["mission_id"]

    request(tmp_path, "complete_step", step=1, mission_id=mission_id)
    refreshed = request(tmp_path, "dashboard")

    assert refreshed["today"]["progress"]["completed"] == 1


def test_desktop_bridge_rejects_unknown_action(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported desktop action"):
        request(tmp_path, "launch_rocket")
