from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumen_lab.desktop_bridge import dispatch


def _request(action: str, *, locale: str, **payload: object):
    return dispatch(
        {
            "action": action,
            "user_id": "default",
            "locale": locale,
            "payload": payload,
        }
    )


def test_locale_switch_relocalizes_starter_work_without_resetting_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    dashboard = _request(
        "guided_onboard",
        locale="en",
        display_name="Alex",
        current_context="I work on backend systems and prepare for interviews",
        desired_change="I want to move into a stronger AI engineering role",
        friction="Limited energy after work",
        focus_minutes=30,
    )
    mission_id = dashboard["today"]["mission_id"]
    workspace = tmp_path / ".lumen" / "users" / "default"

    before_missions = json.loads((workspace / "missions.json").read_text(encoding="utf-8"))
    before_ids = [item["id"] for item in before_missions if item["id"].startswith("personal-")]

    progressed = _request(
        "complete_step",
        locale="en",
        mission_id=mission_id,
        step=1,
    )
    assert progressed["progress"]["completed"] == 1

    russian = _request("bootstrap", locale="ru")
    russian_dashboard = russian["dashboard"]
    after_missions = json.loads((workspace / "missions.json").read_text(encoding="utf-8"))
    after_ids = [item["id"] for item in after_missions if item["id"].startswith("personal-")]
    sessions = json.loads((workspace / "work_sessions.json").read_text(encoding="utf-8"))
    context = json.loads((workspace / "onboarding_context.json").read_text(encoding="utf-8"))

    assert after_ids == before_ids
    assert context["locale"] == "ru"
    assert russian_dashboard["today"]["mission_id"] == mission_id
    assert russian_dashboard["today"]["progress"]["completed"] == 1
    assert russian_dashboard["today"]["focus_minutes"] == 30
    assert any("Продвинуться" in item["title"] for item in after_missions if item["id"] in before_ids)
    assert all(
        item["focus_minutes"] == 30 for item in sessions if item["mission_id"] in before_ids
    )

    english = _request("bootstrap", locale="en")
    restored_missions = json.loads((workspace / "missions.json").read_text(encoding="utf-8"))
    restored_ids = [
        item["id"] for item in restored_missions if item["id"].startswith("personal-")
    ]

    assert restored_ids == before_ids
    assert english["dashboard"]["today"]["mission_id"] == mission_id
    assert english["dashboard"]["today"]["progress"]["completed"] == 1
    assert english["dashboard"]["today"]["focus_minutes"] == 30
    assert any("Move " in item["title"] for item in restored_missions if item["id"] in before_ids)


def test_desktop_bootstrap_prefers_explicit_requested_locale() -> None:
    source = Path("apps/desktop/src/App.tsx").read_text(encoding="utf-8")
    assert (
        "result.dashboard?.locale ?? result.locale ?? result.context?.locale"
        in source
    )
