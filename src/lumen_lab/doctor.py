from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .holdout import FrozenCalibrationBaseline, analyze_holdout, load_baseline
from .ledger import Outcome
from .models import Experiment
from .provenance import load_provenance, validate_provenance
from .replenishment import load_candidate_registry
from .synthesis import render_synthesis


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True, slots=True)
class DoctorReport:
    checks: tuple[CheckResult, ...]

    @property
    def healthy(self) -> bool:
        return all(check.passed for check in self.checks)


def _read_list(path: Path, label: str) -> list[object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{label} must contain a JSON list")
    return raw


def _load_experiments(path: Path) -> list[Experiment]:
    raw = _read_list(path, "backlog")
    experiments: list[Experiment] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("backlog entries must be JSON objects")
        experiments.append(Experiment.from_dict(item))
    return experiments


def _load_outcomes(path: Path) -> list[Outcome]:
    raw = _read_list(path, "outcomes")
    outcomes: list[Outcome] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("outcome entries must be JSON objects")
        outcomes.append(Outcome.from_dict(item))
    return outcomes


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def run_doctor(root: Path) -> DoctorReport:
    state = root / "state"
    checks: list[CheckResult] = []
    experiments: list[Experiment] | None = None
    outcomes: list[Outcome] | None = None
    baseline: FrozenCalibrationBaseline | None = None

    try:
        experiments = _load_experiments(state / "backlog.json")
        duplicate_ids = _duplicates([item.id for item in experiments])
        if duplicate_ids:
            raise ValueError(f"duplicate experiment ids: {', '.join(duplicate_ids)}")
        checks.append(CheckResult("backlog", True, f"{len(experiments)} unique experiments"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        checks.append(CheckResult("backlog", False, str(exc)))

    try:
        outcomes = _load_outcomes(state / "outcomes.json")
        duplicate_ids = _duplicates([item.experiment_id for item in outcomes])
        if duplicate_ids:
            raise ValueError(f"duplicate outcome ids: {', '.join(duplicate_ids)}")
        checks.append(CheckResult("outcomes", True, f"{len(outcomes)} unique outcomes"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        checks.append(CheckResult("outcomes", False, str(exc)))

    if experiments is None or outcomes is None:
        checks.append(
            CheckResult(
                "experiment-outcome-links",
                False,
                "backlog and outcomes must both be valid before links can be checked",
            )
        )
    else:
        experiment_by_id = {item.id: item for item in experiments}
        outcome_ids = {item.experiment_id for item in outcomes}
        problems: list[str] = []
        for outcome in sorted(outcomes, key=lambda item: item.experiment_id):
            experiment = experiment_by_id.get(outcome.experiment_id)
            if experiment is None:
                problems.append(f"orphan outcome {outcome.experiment_id}")
            elif experiment.status != "done":
                problems.append(
                    f"outcome {outcome.experiment_id} references status {experiment.status}"
                )
        for experiment in sorted(experiments, key=lambda item: item.id):
            if experiment.status == "done" and experiment.id not in outcome_ids:
                problems.append(f"done experiment {experiment.id} has no outcome")
        if problems:
            checks.append(CheckResult("experiment-outcome-links", False, "; ".join(problems)))
        else:
            checks.append(
                CheckResult(
                    "experiment-outcome-links",
                    True,
                    "every outcome references done work and every done experiment has one outcome",
                )
            )

    if experiments is None or outcomes is None:
        checks.append(
            CheckResult(
                "provenance",
                False,
                "valid backlog and outcomes are required before provenance can be checked",
            )
        )
    else:
        try:
            records = load_provenance(state / "provenance.json")
            validate_provenance(root, experiments, outcomes, records)
            checks.append(
                CheckResult(
                    "provenance",
                    True,
                    f"{len(records)} completed experiment provenance record(s)",
                )
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            checks.append(CheckResult("provenance", False, str(exc)))

    try:
        candidates = load_candidate_registry(state / "candidates.json")
        checks.append(
            CheckResult("candidate-registry", True, f"{len(candidates)} validated candidates")
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        checks.append(CheckResult("candidate-registry", False, str(exc)))

    try:
        baseline = load_baseline(state / "calibration_baseline.json")
        if outcomes is None:
            raise ValueError("outcomes must be valid before baseline membership can be checked")
        outcome_ids = {item.experiment_id for item in outcomes}
        missing = sorted(set(baseline.training_experiment_ids) - outcome_ids)
        if missing:
            raise ValueError(f"baseline training ids missing from outcomes: {', '.join(missing)}")
        checks.append(
            CheckResult(
                "calibration-baseline",
                True,
                f"version {baseline.version}; {len(baseline.training_experiment_ids)} training ids",
            )
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        checks.append(CheckResult("calibration-baseline", False, str(exc)))

    if baseline is None or outcomes is None:
        checks.append(
            CheckResult(
                "holdout-evaluation",
                False,
                "valid outcomes and calibration baseline are required",
            )
        )
    else:
        try:
            checkpoint = analyze_holdout(outcomes, baseline)
            checks.append(
                CheckResult(
                    "holdout-evaluation",
                    True,
                    f"{checkpoint.holdout_count} holdout outcome(s); {checkpoint.direction}",
                )
            )
        except ValueError as exc:
            checks.append(CheckResult("holdout-evaluation", False, str(exc)))

    if experiments is None or outcomes is None:
        checks.append(
            CheckResult(
                "synthesis",
                False,
                "valid backlog and outcomes are required before synthesis can be checked",
            )
        )
    else:
        try:
            journal_text = (state / "journal.md").read_text(encoding="utf-8")
            actual = (state / "SYNTHESIS.md").read_text(encoding="utf-8")
            expected = render_synthesis(experiments, outcomes, journal_text)
            if actual != expected:
                raise ValueError(
                    "state/SYNTHESIS.md is stale; regenerate it with "
                    "lumen-synthesize --write"
                )
            checks.append(CheckResult("synthesis", True, "snapshot matches deterministic render"))
        except (OSError, ValueError) as exc:
            checks.append(CheckResult("synthesis", False, str(exc)))

    return DoctorReport(tuple(checks))
