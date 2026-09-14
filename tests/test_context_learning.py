from __future__ import annotations

from pathlib import Path

import pytest

from lumen_lab.context_learning import (
    answer_context_clarification,
    clarification_for_context,
    observe_context_signal,
)
from lumen_lab.desktop_bridge import dispatch
from lumen_lab.onboarding import onboarding_context_payload, save_onboarding_context


def _request(action: str, *, user_id: str = "default", **payload: object):
    return dispatch(
        {
            "action": action,
            "user_id": user_id,
            "payload": payload,
        }
    )


def _context_path(tmp_path: Path) -> Path:
    return tmp_path / "context.json"


def _goal_confidence(context: dict) -> float:
    return next(
        item["confidence"]
        for item in context["hypotheses"]
        if item["key"] == "primary_goal"
    )


def test_not_now_tracks_deferral_without_rejecting_goal(tmp_path: Path) -> None:
    path = _context_path(tmp_path)
    context = onboarding_context_payload(
        current_context="Working full time",
        desired_change="I want to ship an AI product",
        focus_minutes=30,
    )
    save_onboarding_context(path, context)
    before = _goal_confidence(context)

    updated = observe_context_signal(
        path,
        mission_id="m1",
        mission_tags=["Ship an AI product"],
        signal="not_now",
    )

    assert updated is not None
    assert _goal_confidence(updated) == before
    assert updated["learning"]["primary_goal_deferrals"] == 1
    assert updated["learning"]["primary_goal_conflict"] == 0


def test_explicit_negative_signals_lower_confidence_and_trigger_question(tmp_path: Path) -> None:
    path = _context_path(tmp_path)
    save_onboarding_context(
        path,
        onboarding_context_payload(
            current_context="Working full time",
            desired_change="I want to ship an AI product",
            focus_minutes=30,
        ),
    )

    for mission_id in ("m1", "m2"):
        context = observe_context_signal(
            path,
            mission_id=mission_id,
            mission_tags=["Ship an AI product"],
            signal="less_like_this",
        )

    assert context is not None
    assert _goal_confidence(context) == 0.58
    clarification = clarification_for_context(context)
    assert clarification is not None
    assert clarification["id"] == "primary_goal_fit"
    assert "Ship an AI product" in clarification["prompt"]


def test_positive_signal_increases_goal_confidence(tmp_path: Path) -> None:
    path = _context_path(tmp_path)
    initial = onboarding_context_payload(
        current_context="Building side projects",
        desired_change="Launch a useful product",
        focus_minutes=30,
    )
    save_onboarding_context(path, initial)

    updated = observe_context_signal(
        path,
        mission_id="m1",
        mission_tags=["Launch a useful product"],
        signal="mission_completed",
    )

    assert updated is not None
    assert _goal_confidence(updated) == 0.84
    assert updated["learning"]["primary_goal_support"] == 1


def test_repeated_deferral_can_shrink_focus_window(tmp_path: Path) -> None:
    path = _context_path(tmp_path)
    save_onboarding_context(
        path,
        onboarding_context_payload(
            current_context="Work and study",
            desired_change="Build my portfolio",
            focus_minutes=60,
        ),
    )
    for index in range(3):
        context = observe_context_signal(
            path,
            mission_id=f"m{index}",
            mission_tags=["Build my portfolio"],
            signal="not_now",
        )

    assert context is not None
    clarification = clarification_for_context(context)
    assert clarification is not None
    assert clarification["id"] == "repeated_deferral"

    updated, effects = answer_context_clarification(
        path,
        clarification_id="repeated_deferral",
        choice="make_smaller",
    )
    assert effects["focus_minutes"] == 30
    assert effects["resume_mission_id"] == "m2"
    assert updated["answers"]["focus_minutes"] == 30
    assert clarification_for_context(updated) is None


def test_desktop_reactions_update_context_and_surface_clarification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    dashboard = _request(
        "guided_onboard",
        display_name="Alex",
        current_context="Working full time",
        desired_change="I want to build an AI product",
        focus_minutes=30,
        friction="",
    )
    mission_id = dashboard["today"]["mission_id"]

    first = _request(
        "react",
        reaction="less_like_this",
        mission_id=mission_id,
    )
    assert first["clarification"] is None

    second = _request(
        "react",
        reaction="less_like_this",
        mission_id=mission_id,
    )
    assert second["clarification"]["id"] == "primary_goal_fit"
    assert _goal_confidence(second["context"]) == 0.58

    answered = _request(
        "clarify_context",
        clarification_id="primary_goal_fit",
        choice="keep_goal",
    )
    assert answered["clarification"] is None
    assert _goal_confidence(answered["context"]) >= 0.76


def test_pausing_goal_removes_its_missions_from_today(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    dashboard = _request(
        "guided_onboard",
        display_name="Alex",
        current_context="Working full time",
        desired_change="I want to build an AI product",
        focus_minutes=30,
        friction="",
    )
    mission_id = dashboard["today"]["mission_id"]
    for _ in range(2):
        dashboard = _request(
            "react",
            reaction="less_like_this",
            mission_id=mission_id,
        )

    paused = _request(
        "clarify_context",
        clarification_id="primary_goal_fit",
        choice="pause_goal",
    )

    assert paused["today"] is None
    assert paused["summary"]["active_missions"] == 0
    assert len(paused["paused"]) == 3


def test_desktop_bootstrap_decorates_existing_dashboard_with_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    _request(
        "guided_onboard",
        display_name="Alex",
        current_context="Working full time",
        desired_change="Build a product",
        focus_minutes=30,
        friction="",
    )

    bootstrap = _request("bootstrap")

    assert bootstrap["context"] is not None
    assert bootstrap["dashboard"]["context"] == bootstrap["context"]
    assert "clarification" in bootstrap["dashboard"]
