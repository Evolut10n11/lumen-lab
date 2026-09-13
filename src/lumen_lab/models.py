from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class Experiment:
    id: str
    title: str
    hypothesis: str
    impact: int
    learning: int
    feasibility: int
    novelty: int
    risk: int
    status: str = "backlog"

    def score(self) -> float:
        """Return a deterministic priority score in roughly the 0..10 range."""
        upside = (
            self.impact * 0.35
            + self.learning * 0.30
            + self.feasibility * 0.20
            + self.novelty * 0.15
        )
        penalty = self.risk * 0.25
        return round(upside - penalty, 2)

    def validate(self) -> None:
        if self.status not in {"backlog", "active", "done", "dropped"}:
            raise ValueError(f"invalid status: {self.status}")
        for field_name in ("impact", "learning", "feasibility", "novelty", "risk"):
            value = getattr(self, field_name)
            if not 1 <= value <= 10:
                raise ValueError(f"{field_name} must be between 1 and 10")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Experiment":
        experiment = cls(**data)
        experiment.validate()
        return experiment
