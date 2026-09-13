from lumen_lab.ledger import Outcome
from lumen_lab.ranking import analyze_ranking


def outcome(
    identifier: str,
    expected: float,
    observed: int,
    learning: int | None = None,
) -> Outcome:
    return Outcome(
        experiment_id=identifier,
        expected_score=expected,
        observed_value=observed,
        learning_value=observed if learning is None else learning,
        result="test",
    )


def test_ranking_requires_minimum_evidence() -> None:
    report = analyze_ranking(
        [outcome(f"exp-{index}", float(index + 1), index + 1) for index in range(4)]
    )

    assert report.direction == "insufficient-data"
    assert report.action == "collect-more-outcomes"


def test_perfect_ordering_is_supported() -> None:
    report = analyze_ranking(
        [outcome(f"exp-{index}", float(index), index) for index in range(1, 6)]
    )

    assert report.comparable_pairs == 10
    assert report.concordant == 10
    assert report.discordant == 0
    assert report.accuracy == 1.0
    assert report.direction == "ranking-supported"


def test_reversed_ordering_is_weak() -> None:
    report = analyze_ranking(
        [
            outcome("exp-1", 1.0, 5),
            outcome("exp-2", 2.0, 4),
            outcome("exp-3", 3.0, 3),
            outcome("exp-4", 4.0, 2),
            outcome("exp-5", 5.0, 1),
        ]
    )

    assert report.concordant == 0
    assert report.discordant == 10
    assert report.accuracy == 0.0
    assert report.direction == "ranking-weak"
    assert report.action == "investigate-feature-weights"


def test_ties_are_excluded_from_accuracy_denominator() -> None:
    report = analyze_ranking(
        [
            outcome("exp-a", 1.0, 1),
            outcome("exp-b", 2.0, 2),
            outcome("exp-c", 3.0, 2),
            outcome("exp-d", 4.0, 4),
            outcome("exp-e", 5.0, 5),
        ]
    )

    assert report.total_pairs == 10
    assert report.observed_ties == 1
    assert report.comparable_pairs == 9
    assert report.concordant == 9
    assert report.accuracy == 1.0


def test_expected_ties_are_counted_separately() -> None:
    report = analyze_ranking(
        [
            outcome("exp-a", 1.0, 1),
            outcome("exp-b", 1.0, 2),
            outcome("exp-c", 3.0, 3),
            outcome("exp-d", 4.0, 4),
            outcome("exp-e", 5.0, 5),
        ]
    )

    assert report.expected_ties == 1
    assert report.comparable_pairs == 9


def test_current_eight_outcomes_support_relative_ranking() -> None:
    outcomes = [
        outcome("exp-003", 7.95, 8, 9),
        outcome("exp-001", 6.75, 8, 8),
        outcome("exp-002", 6.65, 8, 9),
        outcome("exp-004", 6.20, 8, 9),
        outcome("exp-005", 8.20, 9, 9),
        outcome("exp-006", 7.85, 8, 10),
        outcome("exp-008", 7.60, 8, 9),
        outcome("exp-007", 6.95, 8, 8),
    ]

    report = analyze_ranking(outcomes)

    assert report.total_pairs == 28
    assert report.comparable_pairs == 21
    assert report.observed_ties == 7
    assert report.expected_ties == 0
    assert report.concordant == 16
    assert report.discordant == 5
    assert report.accuracy == 0.7619
    assert report.direction == "ranking-supported"
    assert report.action == "hold-relative-weights"
    assert report.calibration_mae == 1.08
    assert report.mean_signed_residual == 1.08
