from __future__ import annotations

import pytest

import lumen_lab.replenishment as replenishment
from lumen_lab.models import Experiment
from lumen_lab.replenishment import apply_replenishment, replenishment_candidates


def experiment(identifier: str, status: str = "done") -> Experiment:
    return Experiment(
        id=identifier,
        title=identifier,
        hypothesis="test",
        impact=5,
        learning=5,
        feasibility=5,
        novelty=5,
        risk=1,
        status=status,
    )


def test_empty_pending_queue_yields_curated_second_generation() -> None:
    candidates = replenishment_candidates([experiment("exp-001")])

    assert [item.id for item in candidates] == ["exp-006", "exp-007", "exp-008"]
    assert all(item.status == "backlog" for item in candidates)
    assert all(1 <= item.score() <= 10 for item in candidates)


def test_pending_work_blocks_replenishment() -> None:
    experiments = [experiment("exp-001"), experiment("exp-999", status="backlog")]

    assert replenishment_candidates(experiments) == []


def test_existing_candidate_ids_are_never_duplicated() -> None:
    experiments = [experiment("exp-001"), experiment("exp-006")]

    candidates = replenishment_candidates(experiments)

    assert [item.id for item in candidates] == ["exp-007", "exp-008"]


def test_invalid_curated_candidate_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    invalid = Experiment(
        id="exp-bad",
        title="invalid",
        hypothesis="invalid",
        impact=11,
        learning=5,
        feasibility=5,
        novelty=5,
        risk=1,
    )
    monkeypatch.setattr(replenishment, "_CURATED_NEXT_GENERATION", (invalid,))

    with pytest.raises(ValueError, match="impact must be between 1 and 10"):
        replenishment_candidates([experiment("exp-001")])


def test_apply_returns_new_state_without_mutating_input() -> None:
    experiments = [experiment("exp-001")]

    updated, added = apply_replenishment(experiments)

    assert [item.id for item in experiments] == ["exp-001"]
    assert [item.id for item in added] == ["exp-006", "exp-007", "exp-008"]
    assert [item.id for item in updated] == ["exp-001", "exp-006", "exp-007", "exp-008"]
