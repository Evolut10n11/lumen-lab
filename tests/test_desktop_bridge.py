from pathlib import Path

import pytest

from lumen_lab.desktop_bridge import dispatch


def request(action: str, *, user_id: str = "default", **payload: object):
    return dispatch(
        {
            "action": action,
            "user_id": user_id,
            "payload": payload,
        }
    )


def test_desktop_bootstrap_starts_in_onboarding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    payload = request("bootstrap")

    assert payload["initialized"] is False
    assert payload["selected_user_id"] == "default"
    assert payload["onboarding"]["mode"] == "quick"


def test_desktop_quick_onboard_returns_product_dashboard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    dashboard = request(
        "quick_onboard",
        display_name="Alex",
        goals=["Build my AI career", "Ship a product"],
    )

    assert dashboard["user"]["display_name"] == "Alex"
    assert dashboard["experience"]["primary_action"]["action"] == "continue"
    assert dashboard["today"]["steps"]


def test_desktop_reaction_updates_only_selected_user(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    request("quick_onboard", display_name="Alex", goals=["Career"])
    request(
        "quick_onboard",
        user_id="bob",
        display_name="Bob",
        goals=["Fitness"],
    )

    alex_before = request("dashboard")
    mission_id = alex_before["today"]["mission_id"]
    alex_after = request(
        "react",
        reaction="more_like_this",
        mission_id=mission_id,
    )
    bob = request("dashboard", user_id="bob")

    assert alex_after["personalization"]["signal_count"] == 1
    assert bob["personalization"]["signal_count"] == 0


def test_desktop_complete_step_persists_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    dashboard = request("quick_onboard", display_name="Alex", goals=["Career"])
    mission_id = dashboard["today"]["mission_id"]

    refreshed = request("complete_step", step=1, mission_id=mission_id)

    assert refreshed["today"]["progress"]["completed"] == 1


def test_desktop_can_resume_a_deferred_mission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    dashboard = request("quick_onboard", display_name="Alex", goals=["Career"])
    mission_id = dashboard["today"]["mission_id"]

    deferred = request("react", reaction="not_now", mission_id=mission_id)
    resumed = request("resume_mission", mission_id=mission_id)

    assert [item["id"] for item in deferred["paused"]] == [mission_id]
    assert resumed["paused"] == []
    assert mission_id in {item["id"] for item in resumed["radar"]}


def test_desktop_bridge_rejects_unknown_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="unsupported desktop action"):
        request("launch_rocket")


def test_desktop_bridge_ignores_caller_controlled_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trusted_root = tmp_path / "trusted"
    attacker_root = tmp_path / "attacker"
    trusted_root.mkdir()
    attacker_root.mkdir()
    monkeypatch.chdir(trusted_root)

    payload = dispatch(
        {
            "root": str(attacker_root),
            "action": "quick_onboard",
            "user_id": "default",
            "payload": {
                "display_name": "Alex",
                "goals": ["Career"],
            },
        }
    )

    assert payload["user"]["display_name"] == "Alex"
    assert (trusted_root / ".lumen" / "users" / "default" / "profile.json").is_file()
    assert not (attacker_root / ".lumen").exists()
