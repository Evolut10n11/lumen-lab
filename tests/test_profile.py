from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumen_lab.mission_radar import Mission, mission_score, ranked_missions
from lumen_lab.profile import Profile, load_profile
from lumen_lab.work_session import choose_mission


def profile_raw(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": "test-profile",
        "display_name": "Test Profile",
        "priorities": {"career": 10, "robotics": 1},
        "skills": ["python"],
        "interests": ["ai"],
        "constraints": ["local-first"],
        "preferred_stack": ["python"],
        "risk_tolerance": 5,
        "candidate_generation_policy": {
            "mode": "reviewed",
            "allow_llm": False,
            "max_candidates": 5,
        },
    }
    data.update(overrides)
    return data


def mission(identifier: str, tag: str) -> Mission:
    return Mission(
        id=identifier,
        title=identifier,
        why_now="Useful now",
        next_action="Do one thing",
        impact=8,
        urgency=7,
        leverage=8,
        momentum=6,
        effort=5,
        risk=2,
        tags=(tag,),
    )


def test_profile_round_trip_loads_explicit_local_state(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(profile_raw()), encoding="utf-8")

    profile = load_profile(path)

    assert profile.id == "test-profile"
    assert profile.priority_for("CAREER") == 10
    assert profile.candidate_generation_policy.mode == "reviewed"


def test_rejects_unknown_profile_fields() -> None:
    raw = profile_raw(extra="nope")
    with pytest.raises(ValueError, match="unknown profile fields"):
        Profile.from_dict(raw)


def test_rejects_normalized_duplicate_list_values() -> None:
    raw = profile_raw(skills=["Python", " python "])
    with pytest.raises(ValueError, match="duplicate value"):
        Profile.from_dict(raw)


def test_rejects_invalid_priority_weight() -> None:
    raw = profile_raw(priorities={"career": 11})
    with pytest.raises(ValueError, match="integer from 1 to 10"):
        Profile.from_dict(raw)


def test_llm_permission_requires_optional_llm_policy() -> None:
    raw = profile_raw(
        candidate_generation_policy={
            "mode": "reviewed",
            "allow_llm": True,
            "max_candidates": 5,
        }
    )
    with pytest.raises(ValueError, match="requires mode optional-llm"):
        Profile.from_dict(raw)


def test_two_profiles_rank_the_same_portfolio_differently() -> None:
    career = mission("career", "career")
    robotics = mission("robotics", "robotics")
    career_profile = Profile.from_dict(profile_raw())
    robotics_profile = Profile.from_dict(
        profile_raw(
            id="robotics-profile",
            priorities={"career": 1, "robotics": 10},
        )
    )

    assert ranked_missions([robotics, career], career_profile)[0].id == "career"
    assert ranked_missions([career, robotics], robotics_profile)[0].id == "robotics"
    assert choose_mission([robotics, career], profile=career_profile).id == "career"
    assert choose_mission([career, robotics], profile=robotics_profile).id == "robotics"


def test_no_profile_keeps_base_scoring_behavior() -> None:
    item = mission("mission", "career")

    assert mission_score(item) == item.score
    assert ranked_missions([item])[0] == item


def test_profile_score_exposes_alignment_without_mutating_base_score() -> None:
    item = mission("career", "career")
    profile = Profile.from_dict(profile_raw())
    base = item.score

    personalized = mission_score(item, profile)

    assert personalized > base
    assert item.score == base
