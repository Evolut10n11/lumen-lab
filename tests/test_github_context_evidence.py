from __future__ import annotations

from pathlib import Path

from lumen_lab.github_user_context import (
    apply_github_evidence,
    build_github_snapshot,
    clear_github_evidence,
)
from lumen_lab.onboarding import (
    load_onboarding_context,
    onboarding_context_payload,
    save_onboarding_context,
)


def test_confirmed_github_context_adds_and_removes_revisable_hypotheses(
    tmp_path: Path,
) -> None:
    snapshot = build_github_snapshot(
        {"login": "alice-dev", "public_repos": 1, "followers": 0},
        [
            {
                "name": "agent-kit",
                "full_name": "alice-dev/agent-kit",
                "owner": {"login": "alice-dev"},
                "description": "Agent tooling",
                "language": "Python",
                "topics": ["ai"],
                "fork": False,
                "archived": False,
                "stargazers_count": 0,
                "pushed_at": "2026-09-12T12:00:00Z",
                "updated_at": "2026-09-12T12:00:00Z",
            }
        ],
        [],
        fetched_at="2026-09-13T12:00:00Z",
    )
    context_path = tmp_path / "onboarding_context.json"
    save_onboarding_context(
        context_path,
        onboarding_context_payload(
            current_context="I am building AI products",
            desired_change="Ship a stronger portfolio",
            focus_minutes=30,
        ),
    )

    apply_github_evidence(context_path, snapshot)
    context = load_onboarding_context(context_path)
    assert context is not None
    by_key = {item["key"]: item for item in context["hypotheses"]}

    assert by_key["github_active_project"]["value"] == "alice-dev/agent-kit"
    assert by_key["github_active_project"]["confidence"] == 0.55
    assert by_key["github_primary_language"]["value"] == "Python"
    assert context["external_evidence"]["github"]["username"] == "alice-dev"

    clear_github_evidence(context_path)
    context = load_onboarding_context(context_path)
    assert context is not None
    keys = {item["key"] for item in context["hypotheses"]}

    assert "github_active_project" not in keys
    assert "github_primary_language" not in keys
    assert "external_evidence" not in context
