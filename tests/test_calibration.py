from lumen_lab.ledger import Outcome, analyze_calibration, residual


def outcome(identifier: str, expected: float, observed: int, learning: int) -> Outcome:
    return Outcome(
        experiment_id=identifier,
        expected_score=expected,
        observed_value=observed,
        learning_value=learning,
        result="test",
    )


def test_residual_is_observed_minus_expected() -> None:
    item = outcome("exp-a", expected=7.0, observed=8, learning=6)
    assert residual(item) == 0.4


def test_checkpoint_requires_five_outcomes() -> None:
    report = analyze_calibration(
        [outcome(f"exp-{index}", expected=7.0, observed=8, learning=8) for index in range(4)]
    )

    assert report.sample_size == 4
    assert report.direction == "insufficient-data"
    assert report.action == "collect-more-outcomes"


def test_systematic_underprediction_holds_relative_weights() -> None:
    report = analyze_calibration(
        [outcome(f"exp-{index}", expected=6.0, observed=8, learning=8) for index in range(5)]
    )

    assert report.direction == "systematic-underprediction"
    assert report.underpredicted == 5
    assert report.overpredicted == 0
    assert report.action == "hold-weights"
    assert "global offset" in report.recommendation


def test_systematic_overprediction_holds_relative_weights() -> None:
    report = analyze_calibration(
        [outcome(f"exp-{index}", expected=9.0, observed=6, learning=6) for index in range(5)]
    )

    assert report.direction == "systematic-overprediction"
    assert report.overpredicted == 5
    assert report.action == "hold-weights"


def test_mixed_residuals_are_not_treated_as_global_offset() -> None:
    outcomes = [
        outcome("exp-a", expected=5.0, observed=8, learning=8),
        outcome("exp-b", expected=5.5, observed=8, learning=8),
        outcome("exp-c", expected=6.0, observed=8, learning=8),
        outcome("exp-d", expected=9.5, observed=7, learning=7),
        outcome("exp-e", expected=9.0, observed=6, learning=6),
    ]
    report = analyze_calibration(outcomes)

    assert report.underpredicted == 3
    assert report.overpredicted == 2
    assert report.direction in {"balanced-or-mixed", "mixed-bias"}
    assert report.action == "hold-weights"
