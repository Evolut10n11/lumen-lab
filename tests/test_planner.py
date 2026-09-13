from lumen_lab.models import Experiment
from lumen_lab.planner import choose_next, ranked


def make_experiment(identifier: str, impact: int, risk: int, status: str = "backlog") -> Experiment:
    return Experiment(
        id=identifier,
        title=identifier,
        hypothesis="test hypothesis",
        impact=impact,
        learning=7,
        feasibility=7,
        novelty=7,
        risk=risk,
        status=status,
    )


def test_score_penalizes_risk() -> None:
    safer = make_experiment("safe", impact=8, risk=2)
    riskier = make_experiment("risky", impact=8, risk=8)
    assert safer.score() > riskier.score()


def test_ranked_ignores_non_backlog_items() -> None:
    backlog = make_experiment("backlog", impact=7, risk=2)
    active = make_experiment("active", impact=10, risk=1, status="active")
    assert ranked([active, backlog]) == [backlog]


def test_choose_next_prefers_highest_score() -> None:
    lower = make_experiment("lower", impact=6, risk=4)
    higher = make_experiment("higher", impact=9, risk=1)
    assert choose_next([lower, higher]) is higher


def test_choose_next_returns_none_without_candidates() -> None:
    done = make_experiment("done", impact=10, risk=1, status="done")
    assert choose_next([done]) is None
