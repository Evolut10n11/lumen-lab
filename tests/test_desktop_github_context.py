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


class FakeGitHubClient:
    def fetch(self, username: str):
        return build_github_snapshot(
            {"login": username, "name": "Alice", "public_repos": 1, "followers": 2},
            [
                {
                    "name": "agent-kit",
                    "full_name": f"{username}/agent-kit",
                    "owner": {"login": username},
                    "description": "Agent tooling",
                    "language": "Python",
                    "topics": ["ai", "agents"],
                    "fork": False,
                    "archived": False,
                    "stargazers_count": 1,
                    "pushed_at": "2026-09-12T12:00:00Z",
                    "updated_at": "2026-09-12T12:00:00Z",
                }
            ],
            [],
            fetched_at="2026-09-13T12:00:00Z",
        )


def onboard() -> dict[str, object]:
    return request(
        "guided_onboard",
        display_name="Alice",
        current_context="I am building AI products",
        desired_change="Ship a stronger portfolio",
        friction="Too many parallel tasks",
        focus_minutes=30,
    )


def test_github_preview_does_not_persist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "lumen_lab.desktop_bridge.GitHubPublicContextClient",
        FakeGitHubClient,
    )
    onboard()

    preview = request("github_preview", username="alice-dev")

    assert preview["account"]["username"] == "alice-dev"
    assert not (
        tmp_path / ".lumen" / "users" / "default" / "github_context.json"
    ).exists()


def test_connect_refresh_and_disconnect_github_context(
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
    context_keys = {item["key"] for item in connected["context"]["hypotheses"]}

    assert connected["integrations"]["github"]["connected"] is True
    assert connected["integrations"]["github"]["account"]["username"] == "alice-dev"
    assert "github_active_project" in context_keys
    assert "github_primary_language" in context_keys
    assert connected["today"]["mission_id"].startswith(GITHUB_CONTEXT_MISSION_PREFIX)
    assert connected["today"]["title"] == "Use agent-kit to move Ship a stronger portfolio forward"

    refreshed = request("github_refresh")
    assert refreshed["integrations"]["github"]["connected"] is True
    assert refreshed["today"]["mission_id"].startswith(GITHUB_CONTEXT_MISSION_PREFIX)

    disconnected = request("github_disconnect")
    context_keys = {item["key"] for item in disconnected["context"]["hypotheses"]}

    assert disconnected["integrations"]["github"]["connected"] is False
    assert "github_active_project" not in context_keys
    assert "github_primary_language" not in context_keys
    assert not disconnected["today"]["mission_id"].startswith(GITHUB_CONTEXT_MISSION_PREFIX)
