from __future__ import annotations

import json
from pathlib import Path

from lumen_lab.app_service import LumenApplication
from lumen_lab.profile import load_profile
from lumen_lab.workspace import UserWorkspace


def _broken_workspace(root: Path, content: str = "") -> UserWorkspace:
    workspace = UserWorkspace.from_root(root, "default").ensure()
    workspace.profile_path.write_text(content, encoding="utf-8")
    return workspace


def test_bootstrap_recovers_from_empty_profile_left_by_failed_first_run(tmp_path: Path) -> None:
    workspace = _broken_workspace(tmp_path)

    result = LumenApplication(tmp_path).bootstrap("default", locale="ru")

    assert result["initialized"] is False
    assert result["dashboard"] is None
    assert result["onboarding"] is not None
    assert not workspace.profile_path.exists()
    assert list(workspace.directory.glob("profile.corrupt-*.json"))


def test_bootstrap_recovers_from_malformed_profile_json(tmp_path: Path) -> None:
    workspace = _broken_workspace(tmp_path, "{")

    result = LumenApplication(tmp_path).bootstrap("default")

    assert result["initialized"] is False
    assert not workspace.profile_path.exists()
    backups = list(workspace.directory.glob("profile.corrupt-*.json"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{"


def test_user_can_onboard_after_corrupt_profile_is_quarantined(tmp_path: Path) -> None:
    workspace = _broken_workspace(tmp_path)
    app = LumenApplication(tmp_path)

    assert app.bootstrap("default")["initialized"] is False
    dashboard = app.onboard(
        "default",
        display_name="Иван",
        priorities={"Подготовиться к собеседованию": 10},
        locale="ru",
    )

    assert dashboard["user"]["display_name"] == "Иван"
    assert load_profile(workspace.profile_path).display_name == "Иван"


def test_corrupt_other_user_does_not_break_selected_user_bootstrap(tmp_path: Path) -> None:
    app = LumenApplication(tmp_path)
    app.onboard("alice", display_name="Alice", priorities={"career": 10})
    broken = UserWorkspace.from_root(tmp_path, "bob").ensure()
    broken.profile_path.write_text("{", encoding="utf-8")

    result = app.bootstrap("alice")

    assert result["initialized"] is True
    assert result["dashboard"]["user"]["id"] == "alice"
    assert result["users"] == [{"id": "alice", "display_name": "Alice"}]
    assert not broken.profile_path.exists()
    assert list(broken.directory.glob("profile.corrupt-*.json"))


def test_corrupt_optional_state_is_quarantined_without_losing_profile(tmp_path: Path) -> None:
    app = LumenApplication(tmp_path)
    app.onboard("alice", display_name="Alice", priorities={"career": 10})
    workspace = UserWorkspace.from_root(tmp_path, "alice")
    workspace.work_progress_path.write_text("{", encoding="utf-8")

    result = app.bootstrap("alice")

    assert result["initialized"] is True
    assert result["dashboard"]["user"]["display_name"] == "Alice"
    assert result["dashboard"]["summary"]["completed_steps"] == 0
    assert list(workspace.directory.glob("work_progress.corrupt-*.json"))


def test_out_of_range_progress_is_quarantined_before_mission_finalization(
    tmp_path: Path,
) -> None:
    app = LumenApplication(tmp_path)
    dashboard = app.onboard("alice", display_name="Alice", priorities={"career": 10})
    workspace = UserWorkspace.from_root(tmp_path, "alice")
    mission_id = dashboard["today"]["mission_id"]
    total = dashboard["today"]["progress"]["total"]
    invalid = list(range(1, total)) + [99]
    workspace.work_progress_path.write_text(
        json.dumps({mission_id: invalid}),
        encoding="utf-8",
    )

    recovered = app.bootstrap("alice")

    assert recovered["dashboard"]["today"]["mission_id"] == mission_id
    assert recovered["dashboard"]["today"]["progress"]["completed"] == 0
    assert recovered["dashboard"]["summary"]["completed_missions"] == 0
    assert list(workspace.directory.glob("work_progress.corrupt-*.json"))
