from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MISSIONS_PATH = Path("state/missions.json")
ALLOWED_STATUSES = {"active", "paused", "done"}


@dataclass(frozen=True)
class Mission:
    id: str
    title: str
    why_now: str
    next_action: str
    impact: int
    urgency: int
    leverage: int
    momentum: int
    effort: int
    risk: int
    status: str = "active"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Mission:
        expected = {
            "id",
            "title",
            "why_now",
            "next_action",
            "impact",
            "urgency",
            "leverage",
            "momentum",
            "effort",
            "risk",
            "status",
        }
        unknown = set(raw) - expected
        missing = expected - set(raw)
        if unknown:
            raise ValueError(f"unknown mission fields: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing mission fields: {', '.join(sorted(missing))}")

        mission = cls(**raw)
        mission.validate()
        return mission

    def validate(self) -> None:
        for name in ("id", "title", "why_now", "next_action"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"mission {name} must be a non-empty string")

        for name in ("impact", "urgency", "leverage", "momentum", "effort", "risk"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 10:
                raise ValueError(f"mission {name} must be an integer from 1 to 10")

        if self.status not in ALLOWED_STATUSES:
            allowed = ", ".join(sorted(ALLOWED_STATUSES))
            raise ValueError(f"mission status must be one of: {allowed}")

    @property
    def score(self) -> float:
        feasibility = 11 - self.effort
        value = (
            self.impact * 0.30
            + self.urgency * 0.20
            + self.leverage * 0.25
            + self.momentum * 0.15
            + feasibility * 0.10
            - self.risk * 0.15
        )
        return round(value, 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "why_now": self.why_now,
            "next_action": self.next_action,
            "impact": self.impact,
            "urgency": self.urgency,
            "leverage": self.leverage,
            "momentum": self.momentum,
            "effort": self.effort,
            "risk": self.risk,
            "status": self.status,
            "score": self.score,
        }


def load_missions(path: Path = DEFAULT_MISSIONS_PATH) -> list[Mission]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("mission state must contain a JSON list")

    missions: list[Mission] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("mission entries must be JSON objects")
        mission = Mission.from_dict(item)
        if mission.id in seen:
            raise ValueError(f"duplicate mission id: {mission.id}")
        seen.add(mission.id)
        missions.append(mission)
    return missions


def ranked_missions(missions: list[Mission]) -> list[Mission]:
    active = [mission for mission in missions if mission.status == "active"]
    return sorted(active, key=lambda mission: (-mission.score, mission.id))


def radar_snapshot(missions: list[Mission], top: int = 1) -> list[dict[str, Any]]:
    if top < 1:
        raise ValueError("top must be at least 1")
    return [mission.to_dict() for mission in ranked_missions(missions)[:top]]
