from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumen_lab.mission_radar import load_missions
from lumen_lab.personalization import build_profile, initialize_workspace
from lumen_lab.user_cli import main as user_main
from lumen_lab.work_session_cli import main as work_main
from lumen_lab.workspace import UserWorkspace, validate_user_id


def _profile(user_id: str, priority: str, interest: str, skill: str):
    return build_profile(
        user_id=user_id,
        display_name=user_id.title(),
        priorities={priority: 10},
        interests=[interest],
        skills=[skill],
        constraints=["five hours per week"],
        preferred_stack=[skill],
        risk_tolerance=4,
    )


def test_user_id_rejects_path_traversal() -> None:
    for value in ("../other", "user/name", "user\\name", "", "."):
        with pytest.raises(ValueError):
            validate_user_id(value)


def test_two_users_have_different_state_paths(tmp_path: Path) -> None:
    alice = UserWorkspace.from_root(tmp_path, "alice")
    bob = UserWorkspace.from_root(tmp_path, "bob")

    assert alice.profile_path != bob.profile_path
    assert alice.work_progress_path != bob.work_progress_path
    assert alice.directory.parent == bob.directory.parent


def test_profiles_bootstrap_different_missions(tmp_path: Path) -> None:
    alice = UserWorkspace.from_root(tmp_path, "alice")
    bob = UserWorkspace.from_root(tmp_path, "bob")
    initialize_workspace(alice, _profile("alice", "career", "AI", "Python"))
    initialize_workspace(bob, _profile("bob", "fitness", "running", "coaching"))

    alice_titles = [item.title for item in load_missions(alice.missions_path)]
    bob_titles = [item.title for item in load_missions(bob.missions_path)]

    assert alice_titles != bob_titles
    assert any("career" in title for title in alice_titles)
    assert any("fitness" in title for title in bob_titles)
    assert "running" not in " ".join(alice_titles).casefold()
    assert "ai" not in " ".join(bob_titles).casefold()


def test_user_cli_creates_only_ignored_local_workspace(tmp_path: Path) -> None:
    code = user_main(
        [
            "--root",
            str(tmp_path),
            "--user",
            "designer",
            "init",
            "--name",
            "Dana",
            "--priority",
            "portfolio=10",
            "--interest",
            "typography",
            "--skill",
            "Figma",
        ]
    )

    workspace = UserWorkspace.from_root(tmp_path, "designer")
    assert code == 0
    assert workspace.profile_path.exists()
    assert workspace.missions_path.exists()
    assert workspace.work_sessions_path.exists()
    assert not (tmp_path / "state").exists()


def test_work_cli_uses_selected_user_not_repository_profile(
    tmp_path: Path,
    capsys,
) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / "profile.json").write_text(
        json.dumps(
            {
                "id": "owner-ai-builder",
                "display_name": "Owner AI Builder",
                "priorities": {"AI agents": 10},
                "skills": ["Python"],
                "interests": ["AI"],
                "constraints": [],
                "preferred_stack": ["Python"],
                "risk_tolerance": 5,
                "candidate_generation_policy": {
                    "mode": "reviewed",
                    "allow_llm": False,
                    "max_candidates": 5,
                },
            }
        ),
        encoding="utf-8",
    )

    workspace = UserWorkspace.from_root(tmp_path, "runner")
    initialize_workspace(workspace, _profile("runner", "marathon", "running", "planning"))

    code = work_main(["--root", str(tmp_path), "--user", "runner", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["user_id"] == "runner"
    assert payload["profile_id"] == "runner"
    assert "marathon" in payload["title"].casefold()
    assert "owner-ai-builder" not in json.dumps(payload).casefold()


def test_default_user_requires_onboarding_instead_of_falling_back_to_repo_state(
    tmp_path: Path,
    capsys,
) -> None:
    state = tmp_path / "state"
    state.mkdir()
    (state / "profile.json").write_text("{}", encoding="utf-8")

    code = work_main(["--root", str(tmp_path)])
    output = capsys.readouterr().out

    assert code == 2
    assert "not initialized" in output
    assert "lumen-user" in output
