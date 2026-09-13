from lumen_lab.ledger import Outcome
from lumen_lab.models import Experiment
from lumen_lab.synthesis import journal_section_count, render_synthesis, repeated_lesson_signals


def outcome(identifier: str, result: str) -> Outcome:
    return Outcome(
        experiment_id=identifier,
        expected_score=7.0,
        observed_value=8,
        learning_value=8,
        result=result,
    )


def experiment(identifier: str, title: str, status: str, score_bias: int = 0) -> Experiment:
    return Experiment(
        id=identifier,
        title=title,
        hypothesis="test",
        impact=7 + score_bias,
        learning=7,
        feasibility=7,
        novelty=7,
        risk=2,
        status=status,
    )


def test_journal_section_count_uses_markdown_headings() -> None:
    journal = "# Lab Journal\n\n## One\ntext\n\n## Two\ntext\n"
    assert journal_section_count(journal) == 2


def test_repeated_signal_requires_two_distinct_outcomes() -> None:
    one = [outcome("exp-a", "Added tests and documentation.")]
    assert repeated_lesson_signals(one) == []

    two = one + [outcome("exp-b", "Implemented tests for deterministic behavior.")]
    assert repeated_lesson_signals(two) == [
        ("deterministic-controls", ["exp-b"]),
        ("tests-and-documentation", ["exp-a", "exp-b"]),
    ][1:]


def test_render_synthesis_orders_completed_ids_and_ranked_backlog() -> None:
    experiments = [
        experiment("exp-done-b", "Done B", "done"),
        experiment("exp-low", "Low", "backlog"),
        experiment("exp-high", "High", "backlog", score_bias=2),
        experiment("exp-done-a", "Done A", "done"),
    ]
    text = render_synthesis(experiments, [], "# Lab Journal\n\n## Entry\n")

    assert "Completed IDs: `exp-done-a`, `exp-done-b`" in text
    assert text.index("`exp-high` — High") < text.index("`exp-low` — Low")
    assert "Recorded outcomes: 0" in text
    assert "Calibration MAE: n/a" in text


def test_render_synthesis_is_deterministic() -> None:
    experiments = [experiment("exp-a", "A", "done"), experiment("exp-b", "B", "backlog")]
    outcomes = [
        outcome("exp-a", "Implemented deterministic validation, tests, and documentation."),
        outcome("exp-c", "Added explicit fallback tests and documentation."),
    ]
    journal = "# Lab Journal\n\n## Entry\nBody\n"

    assert render_synthesis(experiments, outcomes, journal) == render_synthesis(
        experiments, outcomes, journal
    )


def test_snapshot_does_not_require_or_mutate_journal_text() -> None:
    journal = "# Lab Journal\n\n## Original\nKeep me intact.\n"
    before = journal
    render_synthesis([], [], journal)
    assert journal == before
