from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


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


def mean_absolute_calibration_error(outcomes: list[Outcome]) -> float | None:
    if not outcomes:
        return None
    return round(
        sum(outcome.calibration_error() for outcome in outcomes) / len(outcomes),
        2,
    )
