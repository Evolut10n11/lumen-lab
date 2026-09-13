import json

import pytest

from lumen_lab.holdout import (
    FrozenCalibrationBaseline,
    analyze_holdout,
    load_baseline,
)
from lumen_lab.ledger import Outcome


def outcome(identifier: str, expected: float, value: int, learning: int) -> Outcome:
    return Outcome(
        experiment_id=identifier,
        expected_score=expected,
        observed_value=value,
        learning_value=learning,
        result="test",
    )


def baseline(*ids: str, intercept: float = 1.0) -> FrozenCalibrationBaseline:
    return FrozenCalibrationBaseline(
        intercept=intercept,
        training_experiment_ids=tuple(ids),
    )


def test_zero_holdouts_is_explicit() -> None:
    outcomes = [outcome("a", 7.0, 8, 8), outcome("b", 7.3, 8, 9)]
    report = analyze_holdout(outcomes, baseline("a", "b"))

    assert report.training_count == 2
    assert report.holdout_count == 0
    assert report.raw_mae is None
    assert report.corrected_mae is None
    assert report.improvement_ratio is None
    assert report.direction == "no-holdout-evidence"


def test_single_holdout_uses_frozen_intercept() -> None:
    outcomes = [
        outcome("a", 7.0, 8, 8),
        outcome("b", 7.3, 8, 9),
        outcome("c", 7.2, 8, 8),
    ]
    report = analyze_holdout(outcomes, baseline("a", "b"))

    assert report.holdout_count == 1
    assert report.raw_mae == 0.8
    assert report.corrected_mae == 0.2
    assert report.improvement_ratio == 0.75
    assert report.observations[0].experiment_id == "c"
    assert report.direction == "holdout-improved"


def test_multiple_holdouts_are_sorted_deterministically() -> None:
    outcomes = [
        outcome("a", 7.0, 8, 8),
        outcome("d", 8.4, 9, 9),
        outcome("c", 7.2, 8, 8),
    ]
    report = analyze_holdout(outcomes, baseline("a"))

    assert [item.experiment_id for item in report.observations] == ["c", "d"]


def test_duplicate_training_ids_are_rejected() -> None:
    frozen = baseline("a", "a")

    with pytest.raises(ValueError, match="unique"):
        frozen.validate()


def test_unknown_training_id_is_rejected() -> None:
    outcomes = [outcome("a", 7.0, 8, 8)]

    with pytest.raises(ValueError, match="missing from ledger"):
        analyze_holdout(outcomes, baseline("a", "missing"))


def test_non_finite_intercept_is_rejected() -> None:
    frozen = baseline("a", intercept=float("inf"))

    with pytest.raises(ValueError, match="finite"):
        frozen.validate()


def test_analysis_does_not_mutate_inputs() -> None:
    outcomes = [
        outcome("a", 7.0, 8, 8),
        outcome("b", 7.2, 8, 8),
    ]
    frozen = baseline("a", intercept=0.94)
    before_ids = frozen.training_experiment_ids
    before_outcomes = [item.to_dict() for item in outcomes]

    analyze_holdout(outcomes, frozen)

    assert frozen.training_experiment_ids == before_ids
    assert [item.to_dict() for item in outcomes] == before_outcomes


def test_load_baseline_validates_json_schema(tmp_path) -> None:
    path = tmp_path / "baseline.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "intercept": 0.94,
                "training_experiment_ids": ["exp-001", "exp-002"],
            }
        ),
        encoding="utf-8",
    )

    frozen = load_baseline(path)

    assert frozen.intercept == 0.94
    assert frozen.training_experiment_ids == ("exp-001", "exp-002")
