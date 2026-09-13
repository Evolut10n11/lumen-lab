from __future__ import annotations

import json
from pathlib import Path

from lumen_lab.doctor import run_doctor
from lumen_lab.ledger import Outcome
from lumen_lab.models import Experiment
from lumen_lab.synthesis import render_synthesis


def experiment(identifier: str, status: str = "done") -> Experiment:
    return Experiment(
        id=identifier,
        title=identifier,
        hypothesis="test hypothesis",
        impact=7,
        learning=7,
        feasibility=7,
        novelty=5,
        risk=1,
        status=status,
    )


def outcome(identifier: str) -> Outcome:
    return Outcome(
        experiment_id=identifier,
        expected_score=6.5,
        observed_value=7,
        learning_value=8,
        result="deterministic tests and documentation",
    )


def write_state(
    root: Path,
    *,
    experiments: list[Experiment] | None = None,
    outcomes: list[Outcome] | None = None,
    candidates: object | None = None,
    training_ids: list[str] | None = None,
    stale_synthesis: bool = False,
) -> None:
    experiments = [experiment("exp-001")] if experiments is None else experiments
    outcomes = [outcome("exp-001")] if outcomes is None else outcomes
    candidates = (
        [experiment("exp-002", status="backlog").to_dict()]
        if candidates is None
        else candidates
    )
    training_ids = ["exp-001"] if training_ids is None else training_ids

    state = root / "state"
    state.mkdir(parents=True)
    (state / "backlog.json").write_text(
        json.dumps([item.to_dict() for item in experiments], indent=2) + "\n",
        encoding="utf-8",
    )
    (state / "outcomes.json").write_text(
        json.dumps([item.to_dict() for item in outcomes], indent=2) + "\n",
        encoding="utf-8",
    )
    (state / "candidates.json").write_text(
        json.dumps(candidates, indent=2) + "\n",
        encoding="utf-8",
    )
    (state / "calibration_baseline.json").write_text(
        json.dumps(
            {
                "version": 1,
                "intercept": 0.5,
                "training_experiment_ids": training_ids,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    journal = "# Lab Journal\n\n## Test\n\nHealthy fixture.\n\n"
    (state / "journal.md").write_text(journal, encoding="utf-8")
    synthesis = render_synthesis(experiments, outcomes, journal)
    if stale_synthesis:
        synthesis += "stale\n"
    (state / "SYNTHESIS.md").write_text(synthesis, encoding="utf-8")


def checks_by_name(root: Path) -> dict[str, tuple[bool, str]]:
    report = run_doctor(root)
    return {check.name: (check.passed, check.detail) for check in report.checks}


def state_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted((root / "state").iterdir())
        if path.is_file()
    }


def test_healthy_state_passes_without_writes(tmp_path: Path) -> None:
    write_state(tmp_path)
    before = state_bytes(tmp_path)

    report = run_doctor(tmp_path)

    assert report.healthy
    assert [check.name for check in report.checks] == [
        "backlog",
        "outcomes",
        "experiment-outcome-links",
        "candidate-registry",
        "calibration-baseline",
        "holdout-evaluation",
        "synthesis",
    ]
    assert state_bytes(tmp_path) == before


def test_duplicate_backlog_ids_fail(tmp_path: Path) -> None:
    write_state(
        tmp_path,
        experiments=[experiment("exp-001"), experiment("exp-001")],
    )

    checks = checks_by_name(tmp_path)

    assert checks["backlog"][0] is False
    assert "duplicate experiment ids: exp-001" in checks["backlog"][1]


def test_duplicate_outcome_ids_fail(tmp_path: Path) -> None:
    write_state(tmp_path, outcomes=[outcome("exp-001"), outcome("exp-001")])

    checks = checks_by_name(tmp_path)

    assert checks["outcomes"][0] is False
    assert "duplicate outcome ids: exp-001" in checks["outcomes"][1]


def test_orphan_outcome_fails_links(tmp_path: Path) -> None:
    write_state(
        tmp_path,
        experiments=[experiment("exp-001"), experiment("exp-002")],
        outcomes=[outcome("exp-001"), outcome("exp-999")],
    )

    checks = checks_by_name(tmp_path)

    assert checks["experiment-outcome-links"][0] is False
    assert "orphan outcome exp-999" in checks["experiment-outcome-links"][1]


def test_outcome_for_non_done_experiment_fails_links(tmp_path: Path) -> None:
    write_state(
        tmp_path,
        experiments=[experiment("exp-001", status="active")],
        outcomes=[outcome("exp-001")],
    )

    checks = checks_by_name(tmp_path)

    assert checks["experiment-outcome-links"][0] is False
    assert "references status active" in checks["experiment-outcome-links"][1]


def test_done_without_outcome_fails_links(tmp_path: Path) -> None:
    write_state(
        tmp_path,
        experiments=[experiment("exp-001"), experiment("exp-002")],
        outcomes=[outcome("exp-001")],
    )

    checks = checks_by_name(tmp_path)

    assert checks["experiment-outcome-links"][0] is False
    assert "done experiment exp-002 has no outcome" in checks["experiment-outcome-links"][1]


def test_malformed_candidate_registry_fails(tmp_path: Path) -> None:
    write_state(tmp_path, candidates={"not": "a list"})

    checks = checks_by_name(tmp_path)

    assert checks["candidate-registry"][0] is False
    assert "candidate registry must contain a JSON list" in checks["candidate-registry"][1]


def test_unknown_baseline_training_id_fails_baseline_and_holdout(tmp_path: Path) -> None:
    write_state(tmp_path, training_ids=["exp-999"])

    checks = checks_by_name(tmp_path)

    assert checks["calibration-baseline"][0] is False
    assert "exp-999" in checks["calibration-baseline"][1]
    assert checks["holdout-evaluation"][0] is False


def test_stale_synthesis_fails(tmp_path: Path) -> None:
    write_state(tmp_path, stale_synthesis=True)

    checks = checks_by_name(tmp_path)

    assert checks["synthesis"][0] is False
    assert "stale" in checks["synthesis"][1]
