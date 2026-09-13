from __future__ import annotations

from pathlib import Path

import pytest

from lumen_lab.feedback import (
    PreferenceFeedback,
    feedback_adjustment,
    load_feedback,
    record_feedback,
)


def test_missing_feedback_file_is_neutral(tmp_path: Path) -> None:
    feedback = load_feedback(tmp_path / "feedback.json")

    assert feedback == PreferenceFeedback.empty()
    assert feedback_adjustment("mission-1", ["career"], feedback) == 0.0


def test_like_builds_bounded_mission_and_tag_affinity(tmp_path: Path) -> None:
    path = tmp_path / "feedback.json"

    for _ in range(8):
        record_feedback(
            path,
            mission_id="mission-1",
            tags=["Career", "Python"],
            sentiment="like",
        )

    feedback = load_feedback(path)
    assert feedback.events == 8
    assert feedback.missions == {"mission-1": 5}
    assert feedback.tags == {"career": 5, "python": 5}
    assert feedback_adjustment("mission-1", ["career"], feedback) == 2.0


def test_not_now_style_feedback_can_avoid_generalizing_to_tags(tmp_path: Path) -> None:
    path = tmp_path / "feedback.json"

    record_feedback(
        path,
        mission_id="mission-1",
        tags=["career"],
        sentiment="dislike",
        include_tags=False,
    )

    feedback = load_feedback(path)
    assert feedback.missions == {"mission-1": -1}
    assert feedback.tags == {}


def test_opposite_feedback_can_return_affinity_to_neutral(tmp_path: Path) -> None:
    path = tmp_path / "feedback.json"
    record_feedback(path, mission_id="mission-1", tags=["career"], sentiment="like")
    record_feedback(path, mission_id="mission-1", tags=["career"], sentiment="dislike")

    feedback = load_feedback(path)
    assert feedback.missions == {}
    assert feedback.tags == {}
    assert feedback.events == 2


def test_rejects_unknown_sentiment(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="sentiment"):
        record_feedback(
            tmp_path / "feedback.json",
            mission_id="mission-1",
            tags=[],
            sentiment="maybe",
        )
