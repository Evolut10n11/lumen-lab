from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


MIN_CALIBRATION_SAMPLES = 5
RESIDUAL_TOLERANCE = 0.05
MATERIAL_BIAS = 0.50


@dataclass(slots=True)
class Outcome:
    experiment_id: str
    expected_score: float
    observed_value: int
    learning_value: int
    result: str

    def validate(self) -> None:
        if not self.experiment_id.strip():
            raise ValueError("experiment_id must not be empty")
        for field_name in ("observed_value", "learning_value"):
            value = getattr(self, field_name)
            if not 1 <= value <= 10:
                raise ValueError(f"{field_name} must be between 1 and 10")

    def observed_score(self) -> float:
        return round(self.observed_value * 0.7 + self.learning_value * 0.3, 2)

    def calibration_error(self) -> float:
        return round(abs(self.expected_score - self.observed_score()), 2)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Outcome:
        outcome = cls(**data)
        outcome.validate()
        return outcome


@dataclass(frozen=True, slots=True)
class CalibrationCheckpoint:
    sample_size: int
    mae: float | None
    mean_signed_error: float | None
    underpredicted: int
    overpredicted: int
    exact: int
    direction: str
    action: str
    recommendation: str


def mean_absolute_calibration_error(outcomes: list[Outcome]) -> float | None:
    if not outcomes:
        return None
    return round(
        sum(outcome.calibration_error() for outcome in outcomes) / len(outcomes),
        2,
    )


def residual(outcome: Outcome) -> float:
    """Return observed minus expected score; positive means underprediction."""
    return round(outcome.observed_score() - outcome.expected_score, 2)


def analyze_calibration(outcomes: list[Outcome]) -> CalibrationCheckpoint:
    residuals = [residual(outcome) for outcome in outcomes]
    sample_size = len(residuals)
    underpredicted = sum(value > RESIDUAL_TOLERANCE for value in residuals)
    overpredicted = sum(value < -RESIDUAL_TOLERANCE for value in residuals)
    exact = sample_size - underpredicted - overpredicted
    mae = mean_absolute_calibration_error(outcomes)
    mean_signed_error = round(sum(residuals) / sample_size, 2) if sample_size else None

    if sample_size < MIN_CALIBRATION_SAMPLES:
        return CalibrationCheckpoint(
            sample_size=sample_size,
            mae=mae,
            mean_signed_error=mean_signed_error,
            underpredicted=underpredicted,
            overpredicted=overpredicted,
            exact=exact,
            direction="insufficient-data",
            action="collect-more-outcomes",
            recommendation=(
                f"Collect at least {MIN_CALIBRATION_SAMPLES} outcomes before considering "
                "a scoring change."
            ),
        )

    assert mean_signed_error is not None
    if underpredicted == sample_size and mean_signed_error >= MATERIAL_BIAS:
        direction = "systematic-underprediction"
        recommendation = (
            "All observed scores exceed their predictions. This is evidence of a global "
            "offset or scale mismatch, not evidence that any relative feature weight is "
            "wrong. Hold the weights and gather more varied outcomes before testing an "
            "intercept or scale adjustment."
        )
    elif overpredicted == sample_size and mean_signed_error <= -MATERIAL_BIAS:
        direction = "systematic-overprediction"
        recommendation = (
            "All observed scores fall below their predictions. This is evidence of a global "
            "offset or scale mismatch, not evidence that any relative feature weight is "
            "wrong. Hold the weights and gather more varied outcomes before testing an "
            "intercept or scale adjustment."
        )
    elif abs(mean_signed_error) < MATERIAL_BIAS:
        direction = "balanced-or-mixed"
        recommendation = (
            "Aggregate signed bias is small. Keep the current weights and collect more "
            "outcomes before attributing residuals to specific scoring features."
        )
    else:
        direction = "mixed-bias"
        recommendation = (
            "Residuals do not move uniformly. Keep the current weights until a later "
            "checkpoint can test residual association with impact, learning, feasibility, "
            "novelty, and risk separately."
        )

    return CalibrationCheckpoint(
        sample_size=sample_size,
        mae=mae,
        mean_signed_error=mean_signed_error,
        underpredicted=underpredicted,
        overpredicted=overpredicted,
        exact=exact,
        direction=direction,
        action="hold-weights",
        recommendation=recommendation,
    )
