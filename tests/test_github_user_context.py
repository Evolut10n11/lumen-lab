from __future__ import annotations

from pathlib import Path

import pytest

from lumen_lab.github_user_context import (
    build_github_snapshot,
    disconnect_github,
    github_integration_payload,
    load_github_snapshot,
    save_github_snapshot,
    validate_github_username,
)


def sample_snapshot() -> dict[str, object]:
    return build_github_snapshot(
        {
            "login": "alice-dev",
            "name": "Alice",
            "bio": "AI engineer",
            "company": "Example",
            "location": "Helsinki",
            "public_repos": 3,
            "followers": 12,
        },
        [
            {
                "name": "agent-kit",
                "full_name": "alice-dev/agent-kit",
                "owner": {"login": "alice-dev"},
                "description": "Agent tooling",
                "language": "Python",
                "topics": ["ai", "agents"],
                "fork": False,
                "archived": False,
                "stargazers_count": 4,
                "pushed_at": "2026-09-12T12:00:00Z",
                "updated_at": "2026-09-12T12:00:00Z",
            },
            {
                "name": "old-web",
                "full_name": "alice-dev/old-web",
                "owner": {"login": "alice-dev"},
                "description": None,
                "language": "TypeScript",
                "topics": ["web"],
                "fork": False,
                "archived": True,
                "stargazers_count": 0,
                "pushed_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        ],
        [
            {
                "repo": {"name": "alice-dev/agent-kit"},
                "created_at": "2026-09-12T12:00:00Z",
            },
            {
                "repo": {"name": "team/shared-project"},
                "created_at": "2026-09-11T12:00:00Z",
            },
        ],
        fetched_at="2026-09-13T12:00:00Z",
    )


def test_validate_github_username() -> None:
    assert validate_github_username("alice-dev") == "alice-dev"
    with pytest.raises(ValueError, match="cannot start or end"):
        validate_github_username("-alice")


def test_snapshot_extracts_active_project_and_public_signals() -> None:
    snapshot = sample_snapshot()

    assert snapshot["account"]["username"] == "alice-dev"
    assert snapshot["signals"]["active_project"] == "alice-dev/agent-kit"
    assert snapshot["signals"]["primary_language"] == "Python"
    assert snapshot["active_repositories"][0]["event_count"] == 1
    assert snapshot["activity_only_repositories"] == [
        {"full_name": "team/shared-project", "event_count": 1}
    ]
    assert snapshot["languages"] == [{"name": "Python", "repository_count": 1}]


def test_snapshot_persists_and_disconnects(tmp_path: Path) -> None:
    path = tmp_path / "github_context.json"
    snapshot = sample_snapshot()

    save_github_snapshot(path, snapshot)
    loaded = load_github_snapshot(path)

    assert loaded == snapshot
    assert github_integration_payload(loaded)["connected"] is True

    disconnect_github(path)

    assert load_github_snapshot(path) is None
    assert github_integration_payload(None)["connected"] is False
