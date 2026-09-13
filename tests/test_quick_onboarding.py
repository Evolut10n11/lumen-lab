from __future__ import annotations

from pathlib import Path

import pytest

from lumen_lab.app_service import LumenApplication


def test_quick_onboard_needs_no_manual_weights(tmp_path: Path) -> None:
    app = LumenApplication(tmp_path)

    payload = app.quick_onboard(
        "alice",
        display_name="Alice",
        goals=["Build an AI portfolio", "Get stronger"],
    )

    assert payload["user"]["priorities"] == {
        "Build an AI portfolio": 10,
        "Get stronger": 8,
    }
    assert payload["experience"]["primary_action"]["label"] == "Start"


def test_quick_onboard_ignores_blank_and_duplicate_goals(tmp_path: Path) -> None:
    app = LumenApplication(tmp_path)

    payload = app.quick_onboard(
        "alice",
        display_name="Alice",
        goals=["Career", " ", "career", "Health"],
    )

    assert payload["user"]["priorities"] == {"Career": 10, "Health": 8}


def test_quick_onboard_requires_at_least_one_goal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one goal"):
        LumenApplication(tmp_path).quick_onboard(
            "alice",
            display_name="Alice",
            goals=[],
        )


def test_quick_onboard_caps_first_run_scope(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at most five goals"):
        LumenApplication(tmp_path).quick_onboard(
            "alice",
            display_name="Alice",
            goals=["one", "two", "three", "four", "five", "six"],
        )
