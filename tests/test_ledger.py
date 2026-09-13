from pathlib import Path

import pytest

from lumen_lab.ledger import Outcome, mean_absolute_calibration_error
from lumen_lab.store import LabStore


def make_outcome(identifier: str, expected: float, observed: int, learning: int) -> Outcome:
    return Outcome(
        experiment_id=identifier,
        expected_score=expected,
        observed_value=observed,
        learning_value=learning,
        result="test result",
    )


def test_observed_score_blends_value_and_learning() -> None:
    outcome = make_outcome("exp-a", expected=7.0, observed=8, learning=6)
    assert outcome.observed_score() == 7.4


def test_calibration_error_is_absolute_gap() -> None:
    outcome = make_outcome("exp-a", expected=6.5, observed=8, learning=6)
    assert outcome.calibration_error() == 0.9


def test_mean_absolute_calibration_error() -> None:
    outcomes = [
        make_outcome("exp-a", expected=6.5, observed=8, learning=6),
        make_outcome("exp-b", expected=8.0, observed=7, learning=7),
    ]
    assert mean_absolute_calibration_error(outcomes) == 0.95


def test_empty_ledger_has_no_error() -> None:
    assert mean_absolute_calibration_error([]) is None


def test_store_rejects_duplicate_outcome(tmp_path: Path) -> None:
    store = LabStore(tmp_path)
    outcome = make_outcome("exp-a", expected=7.0, observed=8, learning=7)
    store.record_outcome(outcome)

    with pytest.raises(ValueError, match="already recorded"):
        store.record_outcome(outcome)
