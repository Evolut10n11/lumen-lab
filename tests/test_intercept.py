from lumen_lab.intercept import analyze_intercept
from lumen_lab.ledger import Outcome


def outcome(identifier: str, expected: float, value: int, learning: int) -> Outcome:
    return Outcome(
        experiment_id=identifier,
        expected_score=expected,
        observed_value=value,
        learning_value=learning,
        result="test",
    )


def constant_bias_outcomes() -> list[Outcome]:
    return [
        outcome("a", 7.0, 8, 8),
        outcome("b", 7.3, 8, 9),
        outcome("c", 7.6, 8, 10),
        outcome("d", 7.7, 9, 8),
        outcome("e", 8.0, 9, 9),
        outcome("f", 8.3, 9, 10),
    ]


def current_ledger() -> list[Outcome]:
    return [
        outcome("exp-003", 7.95, 8, 9),
        outcome("exp-001", 6.75, 8, 8),
        outcome("exp-002", 6.65, 8, 9),
        outcome("exp-004", 6.20, 8, 9),
        outcome("exp-005", 8.20, 9, 9),
        outcome("exp-006", 7.85, 8, 10),
        outcome("exp-008", 7.60, 8, 9),
        outcome("exp-007", 6.95, 8, 8),
        outcome("exp-009", 8.75, 9, 9),
    ]


def test_insufficient_evidence() -> None:
    report = analyze_intercept(constant_bias_outcomes()[:5])

    assert report.direction == "insufficient-data"
    assert report.action == "collect-more-outcomes"


def test_known_constant_bias_is_supported() -> None:
    report = analyze_intercept(constant_bias_outcomes())

    assert report.baseline_mae == 1.0
    assert report.loo_corrected_mae == 0.0
    assert report.improvement_ratio == 1.0
    assert report.proposed_intercept == 1.0
    assert report.ranking_preserved is True
    assert report.direction == "intercept-supported"


def test_mixed_residuals_reject_intercept() -> None:
    outcomes = [
        outcome("a", 7.0, 8, 8),
        outcome("b", 9.0, 8, 8),
        outcome("c", 7.3, 8, 9),
        outcome("d", 9.3, 8, 9),
        outcome("e", 7.6, 8, 10),
        outcome("f", 9.6, 8, 10),
    ]
    report = analyze_intercept(outcomes)

    assert report.proposed_intercept == 0.0
    assert report.direction == "intercept-rejected"
    assert report.action == "hold-current-scale"


def test_leave_one_out_does_not_fit_held_out_residual() -> None:
    outcomes = constant_bias_outcomes()
    outcomes[-1] = outcome("f", 7.3, 9, 10)
    report = analyze_intercept(outcomes)

    assert report.loo_corrected_mae is not None
    assert report.loo_corrected_mae > 0.0


def test_current_ledger_supports_advisory_intercept() -> None:
    report = analyze_intercept(current_ledger())

    assert report.sample_size == 9
    assert report.baseline_mae == 0.99
    assert report.loo_corrected_mae == 0.52
    assert report.improvement_ratio == 0.4705
    assert report.proposed_intercept == 0.99
    assert report.ranking_preserved is True
    assert report.direction == "intercept-supported"
    assert report.action == "consider-intercept-advisory"


def test_constant_shift_preserves_pairwise_order() -> None:
    scores = [6.2, 6.95, 7.6, 8.75]
    intercept = 0.99
    shifted = [score + intercept for score in scores]

    for left in range(len(scores)):
        for right in range(left + 1, len(scores)):
            assert (scores[left] < scores[right]) == (shifted[left] < shifted[right])
