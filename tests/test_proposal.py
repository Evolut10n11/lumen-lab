from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumen_lab.mission_radar import Mission
from lumen_lab.models import Experiment
from lumen_lab.profile import CandidateGenerationPolicy, Profile
from lumen_lab.proposal import (
    OpenAICompatibleProposalGenerator,
    Proposal,
    accept_proposal,
    deterministic_proposals,
    generate_proposals,
    validate_evidence,
)
from lumen_lab.proposal_cli import main


def profile(
    identifier: str,
    priorities: dict[str, int],
    *,
    mode: str = "reviewed",
    allow_llm: bool = False,
    max_candidates: int = 5,
    risk_tolerance: int = 4,
) -> Profile:
    return Profile(
        id=identifier,
        display_name=identifier,
        priorities=priorities,
        skills=("python",),
        interests=("building",),
        constraints=("review-first",),
        preferred_stack=("python",),
        risk_tolerance=risk_tolerance,
        candidate_generation_policy=CandidateGenerationPolicy(
            mode=mode,
            allow_llm=allow_llm,
            max_candidates=max_candidates,
        ),
    )


def mission(identifier: str, tag: str, *, risk: int = 2) -> Mission:
    return Mission(
        id=identifier,
        title=f"{tag.title()} Mission",
        why_now="Useful evidence is missing.",
        next_action=f"Build one bounded {tag} proof",
        impact=8,
        urgency=7,
        leverage=8,
        momentum=7,
        effort=4,
        risk=risk,
        status="active",
        tags=(tag,),
    )


def experiment(identifier: str, title: str = "Existing") -> Experiment:
    return Experiment(
        id=identifier,
        title=title,
        hypothesis="Existing hypothesis",
        impact=7,
        learning=7,
        feasibility=7,
        novelty=5,
        risk=2,
        status="done",
    )


def test_disabled_policy_produces_no_proposals() -> None:
    current = profile("off", {"ai": 10}, mode="disabled", max_candidates=1)
    assert deterministic_proposals(current, [mission("ai", "ai")], []) == []


def test_different_profiles_prioritize_same_portfolio_differently() -> None:
    missions = [mission("ai", "ai"), mission("robotics", "robotics")]
    ai = profile("ai-user", {"ai": 10, "robotics": 1}, max_candidates=1)
    robotics = profile("robot-user", {"ai": 1, "robotics": 10}, max_candidates=1)

    assert deterministic_proposals(ai, missions, [])[0].id == "mission-ai"
    assert deterministic_proposals(robotics, missions, [])[0].id == "mission-robotics"


def test_max_candidates_is_enforced() -> None:
    current = profile("small", {"ai": 10}, max_candidates=1)
    proposals = deterministic_proposals(
        current,
        [mission("one", "ai"), mission("two", "ai")],
        [],
    )
    assert len(proposals) == 1


def test_risk_above_profile_tolerance_is_filtered() -> None:
    current = profile("safe", {"ai": 10}, risk_tolerance=2)
    proposals = deterministic_proposals(current, [mission("risky", "ai", risk=5)], [])
    assert proposals == []


def test_existing_normalized_title_is_not_proposed() -> None:
    current = profile("user", {"ai": 10})
    missions = [mission("ai", "ai")]
    existing = [experiment("exp-001", "  VALIDATE   AI MISSION  ")]
    assert deterministic_proposals(current, missions, existing) == []


def test_unknown_evidence_is_rejected() -> None:
    proposal = Proposal(
        id="candidate-one",
        title="Candidate",
        hypothesis="Test a bounded thing.",
        tags=("ai",),
        impact=8,
        learning=8,
        feasibility=8,
        novelty=7,
        risk=2,
        rationale="Useful.",
        evidence=("mission:invented",),
        source="llm",
    )
    with pytest.raises(ValueError, match="unknown evidence"):
        validate_evidence(proposal, {"mission:real"})


def test_malformed_llm_output_falls_back_to_deterministic() -> None:
    current = profile(
        "llm-user",
        {"ai": 10},
        mode="optional-llm",
        allow_llm=True,
        max_candidates=3,
    )

    def bad_transport(endpoint, payload, headers, timeout):
        return {"choices": [{"message": {"content": "not json"}}]}

    adapter = OpenAICompatibleProposalGenerator(
        endpoint="http://local.invalid/v1/chat/completions",
        model="local",
        transport=bad_transport,
    )
    batch = generate_proposals(current, [mission("ai", "ai")], [], adapter)

    assert [item.source for item in batch.proposals] == ["deterministic"]
    assert batch.warnings == ("LLM proposals failed safely: JSONDecodeError.",)


def test_valid_llm_proposal_is_merged_after_deterministic() -> None:
    current = profile(
        "llm-user",
        {"ai": 10},
        mode="optional-llm",
        allow_llm=True,
        max_candidates=2,
    )

    def transport(endpoint, payload, headers, timeout):
        item = {
            "id": "llm-second",
            "title": "Explore an AI reliability probe",
            "hypothesis": "A small reliability probe will reveal one actionable failure mode.",
            "tags": ["ai"],
            "impact": 8,
            "learning": 9,
            "feasibility": 8,
            "novelty": 8,
            "risk": 2,
            "rationale": "The profile prioritizes AI and the active mission needs evidence.",
            "evidence": ["profile:llm-user", "mission:ai", "profile:priority:ai"],
        }
        return {"choices": [{"message": {"content": json.dumps({"proposals": [item]})}}]}

    adapter = OpenAICompatibleProposalGenerator(
        endpoint="http://local.invalid/v1/chat/completions",
        model="local",
        transport=transport,
    )
    batch = generate_proposals(current, [mission("ai", "ai")], [], adapter)

    assert [item.source for item in batch.proposals] == ["deterministic", "llm"]


def test_acceptance_revalidates_and_creates_normal_backlog_experiment() -> None:
    current = profile("user", {"ai": 10})
    missions = [mission("ai", "ai")]
    proposal = deterministic_proposals(current, missions, [])[0]

    accepted = accept_proposal(proposal, "exp-020", current, missions, [])

    assert accepted.id == "exp-020"
    assert accepted.title == proposal.title
    assert accepted.status == "backlog"


def _write_repo(root: Path) -> None:
    state = root / "state"
    state.mkdir()
    (state / "profile.json").write_text(
        json.dumps(
            {
                "id": "user",
                "display_name": "User",
                "priorities": {"ai": 10},
                "skills": ["python"],
                "interests": ["building"],
                "constraints": ["review-first"],
                "preferred_stack": ["python"],
                "risk_tolerance": 4,
                "candidate_generation_policy": {
                    "mode": "reviewed",
                    "allow_llm": False,
                    "max_candidates": 2,
                },
            }
        ),
        encoding="utf-8",
    )
    item = mission("ai", "ai").to_dict()
    item.pop("score")
    (state / "missions.json").write_text(json.dumps([item]), encoding="utf-8")
    (state / "backlog.json").write_text("[]\n", encoding="utf-8")
    (state / "outcomes.json").write_text("[]\n", encoding="utf-8")
    (state / "journal.md").write_text("# Journal\n", encoding="utf-8")


def test_cli_preview_does_not_write_repository_state(tmp_path: Path, capsys) -> None:
    _write_repo(tmp_path)
    before = {
        path.name: path.read_bytes()
        for path in sorted((tmp_path / "state").iterdir())
        if path.is_file()
    }

    assert main(["--root", str(tmp_path), "--json"]) == 0
    json.loads(capsys.readouterr().out)

    after = {
        path.name: path.read_bytes()
        for path in sorted((tmp_path / "state").iterdir())
        if path.is_file()
    }
    assert after == before


def test_cli_accept_requires_review_snapshot_and_changes_only_backlog(
    tmp_path: Path, capsys
) -> None:
    _write_repo(tmp_path)
    review = tmp_path / "review.json"
    assert main(["--root", str(tmp_path), "--write-review", str(review)]) == 0
    capsys.readouterr()
    state = tmp_path / "state"
    before_other = {
        path.name: path.read_bytes()
        for path in sorted(state.iterdir())
        if path.is_file() and path.name != "backlog.json"
    }

    code = main(
        [
            "--root",
            str(tmp_path),
            "--accept-file",
            str(review),
            "--accept",
            "mission-ai",
            "--experiment-id",
            "exp-020",
        ]
    )

    assert code == 0
    backlog = json.loads((state / "backlog.json").read_text(encoding="utf-8"))
    assert backlog[0]["id"] == "exp-020"
    after_other = {
        path.name: path.read_bytes()
        for path in sorted(state.iterdir())
        if path.is_file() and path.name != "backlog.json"
    }
    assert after_other == before_other
