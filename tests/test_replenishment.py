from __future__ import annotations

import json

import pytest

from lumen_lab.models import Experiment
from lumen_lab.replenishment import (
    apply_replenishment,
    load_candidate_registry,
    replenishment_candidates,
)


def experiment(
    identifier: str,
    status: str = "done",
    *,
    impact: int = 5,
) -> Experiment:
    return Experiment(
        id=identifier,
        title=identifier,
        hypothesis="test",
        impact=impact,
        learning=5,
        feasibility=5,
        novelty=5,
        risk=1,
        status=status,
    )


def test_registry_loader_rejects_non_list(tmp_path) -> None:
    path = tmp_path / "candidates.json"
    path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON list"):
        load_candidate_registry(path)


def test_registry_loader_rejects_duplicate_ids(tmp_path) -> None:
    candidate = experiment("exp-a", status="backlog").to_dict()
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([candidate, candidate]), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate candidate id"):
        load_candidate_registry(path)


def test_registry_loader_rejects_non_backlog_status(tmp_path) -> None:
    candidate = experiment("exp-a", status="done").to_dict()
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([candidate]), encoding="utf-8")

    with pytest.raises(ValueError, match="must have backlog status"):
        load_candidate_registry(path)


def test_registry_loader_reuses_experiment_schema(tmp_path) -> None:
    candidate = experiment("exp-a", status="backlog").to_dict()
    candidate["impact"] = 11
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps([candidate]), encoding="utf-8")

    with pytest.raises(ValueError, match="impact must be between 1 and 10"):
        load_candidate_registry(path)


def test_pending_work_blocks_replenishment() -> None:
    experiments = [experiment("exp-old"), experiment("exp-pending", status="backlog")]
    registry = [experiment("exp-new", status="backlog")]

    assert replenishment_candidates(experiments, registry) == []


def test_existing_ids_are_filtered_without_mutating_registry() -> None:
    experiments = [experiment("exp-old"), experiment("exp-a")]
    registry = [
        experiment("exp-a", status="backlog", impact=8),
        experiment("exp-b", status="backlog", impact=7),
    ]
    before = [item.to_dict() for item in registry]

    candidates = replenishment_candidates(experiments, registry)

    assert [item.id for item in candidates] == ["exp-b"]
    assert [item.to_dict() for item in registry] == before


def test_candidates_are_ranked_deterministically() -> None:
    registry = [
        experiment("exp-low", status="backlog", impact=5),
        experiment("exp-high-b", status="backlog", impact=9),
        experiment("exp-high-a", status="backlog", impact=9),
    ]

    candidates = replenishment_candidates([experiment("exp-old")], registry)

    assert [item.id for item in candidates] == ["exp-high-a", "exp-high-b", "exp-low"]


def test_apply_returns_new_state_without_mutating_inputs() -> None:
    experiments = [experiment("exp-old")]
    registry = [experiment("exp-new", status="backlog")]
    experiments_before = [item.to_dict() for item in experiments]
    registry_before = [item.to_dict() for item in registry]

    updated, added = apply_replenishment(experiments, registry)

    assert [item.id for item in added] == ["exp-new"]
    assert [item.id for item in updated] == ["exp-old", "exp-new"]
    assert [item.to_dict() for item in experiments] == experiments_before
    assert [item.to_dict() for item in registry] == registry_before


def test_exhausted_registry_returns_no_candidates() -> None:
    experiments = [experiment("exp-a"), experiment("exp-b")]
    registry = [
        experiment("exp-a", status="backlog"),
        experiment("exp-b", status="backlog"),
    ]

    assert replenishment_candidates(experiments, registry) == []
