from __future__ import annotations

from pathlib import Path

import pytest

from lumen_lab.desktop_bridge import dispatch
from lumen_lab.onboarding import guided_profile_inputs, onboarding_context_payload


def _request(action: str, *, user_id: str = "default", **payload: object):
    return dispatch(
        {
            "action": action,
            "user_id": user_id,
            "payload": payload,
        }
    )


def test_guided_profile_inputs_turn_normal_language_into_safe_starter_profile() -> None:
    inputs = guided_profile_inputs(
        current_context="I work as a backend developer and prepare for interviews",
        desired_change="I want to get a stronger AI role",
        friction="I keep spreading attention across too many things",
        focus_minutes=30,
    )

    assert inputs["priorities"] == {"Get a stronger AI role": 10}
    assert inputs["interests"] == (
        "I work as a backend developer and prepare for interviews",
    )
    assert inputs["constraints"] == (
        "I keep spreading attention across too many things",
    )
    assert inputs["focus_minutes"] == 30


def test_onboarding_context_keeps_hypotheses_explicit_and_revisable() -> None:
    payload = onboarding_context_payload(
        current_context="Building a pet project",
        desired_change="Ship something people actually use",
        friction="Not enough uninterrupted time",
        focus_minutes=15,
    )

    assert payload["source"] == "conversation"
    assert payload["answers"]["focus_minutes"] == 15
    assert payload["average_confidence"] < 1
    assert {item["key"] for item in payload["hypotheses"]} == {
        "primary_goal",
        "current_context",
        "focus_window",
        "friction",
    }


def test_guided_onboarding_persists_context_and_changes_focus_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    dashboard = _request(
        "guided_onboard",
        display_name="Alex",
        current_context="Working full time and learning AI after work",
        desired_change="I want to ship my own AI product",
        friction="I lose momentum when tasks are too large",
        focus_minutes=30,
    )

    assert dashboard["user"]["display_name"] == "Alex"
    assert dashboard["user"]["priorities"] == {"Ship my own AI product": 10}
    assert dashboard["today"]["focus_minutes"] == 30
    assert dashboard["context"]["answers"]["current_context"].startswith("Working full time")
    assert dashboard["context"]["hypotheses"][0]["confidence"] < 1

    bootstrap = _request("bootstrap")
    assert bootstrap["initialized"] is True
    assert bootstrap["context"] == dashboard["context"]


def test_guided_onboarding_rejects_fake_focus_window() -> None:
    with pytest.raises(ValueError, match="focus_minutes must be one of"):
        guided_profile_inputs(
            current_context="Work",
            desired_change="Grow",
            focus_minutes=45,
        )
