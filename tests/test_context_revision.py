from __future__ import annotations

from pathlib import Path

import pytest

from lumen_lab.desktop_bridge import dispatch
from lumen_lab.github_context_missions import GITHUB_CONTEXT_MISSION_PREFIX
from lumen_lab.github_user_context import build_github_snapshot


def request(action: str, *, user_id: str = "default", **payload: object):
    return dispatch(
        {
            "action": action,
            "user_id": user_id,
            "payload": payload,
        }
    )


def onboard() -> dict[str, object]:
    return request(
        "guided_onboard",
        display_name="Alice",
        current_context="Building AI products",
        desired_change="Ship a stronger portfolio",
        friction="Too many parallel tasks",
        focus_minutes=30,
    )


class FakeGitHubClient:
    def fetch(self, username: str):
        return build_github_snapshot(
            {"login": username, "public_repos": 1, "followers": 0},
            [
                {
                    "name": "agent-kit",
                    "full_name": f"{username}/agent-kit",
                    "owner": {"login": username},
                    "description": "Agent tooling",
                    "language": "Python",
                    "topics": ["ai"],
                    "fork": False,
                    "archived": False,
                    "stargazers_count": 0,
                    "pushed_at": "2026-09-13T12:00:00Z",
                    "updated_at": "2026-09-13T12:00:00Z",
                }
            ],
            [],
            fetched_at="2026-09-13T12:00:00Z",
        )


def hypothesis(context: dict[str, object], key: str) -> dict[str, object]:
    hypotheses = context["hypotheses"]
    assert isinstance(hypotheses, list)
    return next(item for item in hypotheses if isinstance(item, dict) and item.get("key") == key)


def test_revise_direction_rebuilds_current_work_from_new_explicit_goal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    initial = onboard()
    initial_today = initial["today"]
    assert isinstance(initial_today, dict)
    request(
        "complete_step",
        mission_id=initial_today["mission_id"],
        step=1,
    )

    revised = request(
        "revise_direction",
        desired_change="Prepare for robotics interviews",
        current_context="Interview preparation",
        friction="",
        focus_minutes=15,
    )

    assert revised["user"]["priorities"] == {"Prepare for robotics interviews": 10}
    assert revised["user"]["interests"] == [
        "career preparation and visible proof of skill"
    ]
    assert revised["user"]["constraints"] == []
    assert "Prepare for robotics interviews" in revised["today"]["title"]
    assert revised["today"]["focus_minutes"] == 15
    assert revised["summary"]["completed_steps"] == 0
    assert revised["revision"]["old_goal"] == "Ship a stronger portfolio"
    assert revised["revision"]["new_goal"] == "Prepare for robotics interviews"
    assert revised["revision"]["reset_current_progress"] is True

    goal = hypothesis(revised["context"], "primary_goal")
    assert goal["value"] == "Prepare for robotics interviews"
    assert goal["confidence"] == 0.99
    assert goal["source"] == "explicit_revision"
    assert all(
        item.get("key") != "friction"
        for item in revised["context"]["hypotheses"]
        if isinstance(item, dict)
    )
    assert revised["context"]["revisions"][-1]["from"] == "Ship a stronger portfolio"
    assert revised["context"]["revisions"][-1]["to"] == "Prepare for robotics interviews"


def test_revise_direction_preserves_unspecified_context_and_focus(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    onboard()

    revised = request(
        "revise_direction",
        desired_change="Launch one useful product",
    )

    assert revised["today"]["focus_minutes"] == 30
    assert revised["user"]["interests"] == [
        "one user-visible outcome in the current project"
    ]
    assert revised["user"]["constraints"] == ["Too many parallel tasks"]
    assert hypothesis(revised["context"], "current_context")["value"] == "Building AI products"
    assert hypothesis(revised["context"], "friction")["value"] == "Too many parallel tasks"


def test_revise_direction_rebuilds_connected_github_mission_for_new_goal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "lumen_lab.desktop_bridge.GitHubPublicContextClient",
        FakeGitHubClient,
    )
    onboard()
    connected = request("github_connect", username="alice-dev")
    old_id = connected["today"]["mission_id"]
    assert old_id.startswith(GITHUB_CONTEXT_MISSION_PREFIX)

    revised = request(
        "revise_direction",
        desired_change="Become strong at robotics engineering",
    )

    assert revised["integrations"]["github"]["connected"] is True
    assert revised["today"]["mission_id"].startswith(GITHUB_CONTEXT_MISSION_PREFIX)
    assert revised["today"]["mission_id"] != old_id
    assert revised["today"]["title"] == (
        "Use agent-kit to move Become strong at robotics engineering forward"
    )
    assert revised["revision"]["github_mission_id"] == revised["today"]["mission_id"]


def test_revise_direction_rejects_unsupported_focus_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    onboard()

    with pytest.raises(ValueError, match="focus_minutes must be one of"):
        request(
            "revise_direction",
            desired_change="Learn robotics",
            focus_minutes=45,
        )
