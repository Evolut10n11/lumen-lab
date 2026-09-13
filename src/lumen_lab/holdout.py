from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ledger import Outcome, residual

BASELINE_VERSION = 1


@dataclass(frozen=True, slots=True)
class FrozenCalibrationBaseline:
    intercept: float
    training_experiment_ids: tuple[str, ...]
    version: int = BASELINE_VERSION

    def validate(self) -> None:
        if self.version != BASELINE_VERSION:
            raise ValueError(f"unsupported calibration baseline version: {self.version}")
        if not math.isfinite(self.intercept):
            raise ValueError("baseline intercept must be finite")
        if not self.training_experiment_ids:
            raise ValueError("baseline must contain at least one training experiment id")
        if any(not item.strip() for item in self.training_experiment_ids):
            raise ValueError("training experiment ids must not be empty")
        if len(set(self.training_experiment_ids)) != len(self.training_experiment_ids):
            raise ValueError("training experiment ids must be unique")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FrozenCalibrationBaseline:
        ids = data.get("training_experiment_ids")
        if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
            raise ValueError("training_experiment_ids must be a list of strings")
        intercept = data.get("intercept")
        if not isinstance(intercept, (int, float)) or isinstance(intercept, bool):
            raise ValueError("baseline intercept must be numeric")
        version = data.get("version", BASELINE_VERSION)
        if not isinstance(version, int) or isinstance(version, bool):
            raise ValueError("baseline version must be an integer")
        baseline = cls(
            intercept=float(intercept),
            training_experiment_ids=tuple(ids),
            version=version,
        )
        baseline.validate()
        return baseline


@dataclass(frozen=True, slots=True)
class HoldoutObservation:
    experiment_id: str
    residual: float
    raw_error: float
    corrected_error: float


@dataclass(frozen=True, slots=True)
class HoldoutCheckpoint:
    training_count: int
    holdout_count: int
    intercept: float
    raw_mae: float | None
    corrected_mae: float | None
    improvement_ratio: float | None
    observations: tuple[HoldoutObservation, ...]
    direction: str
    action: str
    recommendation: str


def load_baseline(path: Path) -> FrozenCalibrationBaseline:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("calibration baseline must be a JSON object")
    return FrozenCalibrationBaseline.from_dict(data)


def analyze_holdout(
    outcomes: list[Outcome],
    baseline: FrozenCalibrationBaseline,
) -> HoldoutCheckpoint:
    baseline.validate()
    by_id = {outcome.experiment_id: outcome for outcome in outcomes}
    if len(by_id) != len(outcomes):
        raise ValueError("outcome experiment ids must be unique")

    missing = sorted(set(baseline.training_experiment_ids) - set(by_id))
    if missing:
        raise ValueError(f"baseline training ids missing from ledger: {', '.join(missing)}")

    training_ids = set(baseline.training_experiment_ids)
    holdouts = sorted(
        (outcome for outcome in outcomes if outcome.experiment_id not in training_ids),
        key=lambda outcome: outcome.experiment_id,
    )
    observations = tuple(
        HoldoutObservation(
            experiment_id=outcome.experiment_id,
            residual=residual(outcome),
            raw_error=round(abs(residual(outcome)), 2),
            corrected_error=round(abs(residual(outcome) - baseline.intercept), 2),
        )
        for outcome in holdouts
    )

    if not observations:
        return HoldoutCheckpoint(
            training_count=len(training_ids),
            holdout_count=0,
            intercept=baseline.intercept,
            raw_mae=None,
            corrected_mae=None,
            improvement_ratio=None,
            observations=(),
            direction="no-holdout-evidence",
            action="collect-holdout-outcomes",
            recommendation=(
                "The frozen baseline is valid, but no outcome exists outside its training set yet."
            ),
        )

    raw_mae = round(sum(item.raw_error for item in observations) / len(observations), 2)
    corrected_mae = round(
        sum(item.corrected_error for item in observations) / len(observations), 2
    )
    if raw_mae == 0:
        improvement_ratio = 0.0
    else:
        improvement_ratio = round((raw_mae - corrected_mae) / raw_mae, 4)

    if corrected_mae < raw_mae:
        direction = "holdout-improved"
        action = "keep-baseline-frozen"
        recommendation = (
            "The frozen intercept improved current holdout error. Keep the baseline frozen "
            "and collect more holdouts before considering planner integration."
        )
    else:
        direction = "holdout-not-improved"
        action = "keep-baseline-frozen"
        recommendation = (
            "The frozen intercept did not improve current holdout error. Do not deploy it; "
            "keep collecting holdout evidence without refitting this baseline."
        )

    return HoldoutCheckpoint(
        training_count=len(training_ids),
        holdout_count=len(observations),
        intercept=baseline.intercept,
        raw_mae=raw_mae,
        corrected_mae=corrected_mae,
        improvement_ratio=improvement_ratio,
        observations=observations,
        direction=direction,
        action=action,
        recommendation=recommendation,
    )
