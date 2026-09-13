from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .profile import normalized_label

FEEDBACK_SCHEMA_VERSION = 1
MAX_AFFINITY = 5
_SENTIMENT_DELTAS = {"like": 1, "dislike": -1}


def _clamp(value: int) -> int:
    return max(-MAX_AFFINITY, min(MAX_AFFINITY, value))


def _validated_scores(raw: object, name: str) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise ValueError(f"feedback {name} must be a JSON object")

    result: dict[str, int] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"feedback {name} keys must be non-empty strings")
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"feedback {name} values must be integers")
        if not -MAX_AFFINITY <= value <= MAX_AFFINITY:
            raise ValueError(
                f"feedback {name} values must be between {-MAX_AFFINITY} and {MAX_AFFINITY}"
            )
        if value:
            result[key.strip()] = value
    return result


@dataclass(frozen=True, slots=True)
class PreferenceFeedback:
    events: int
    missions: dict[str, int]
    tags: dict[str, int]

    @classmethod
    def empty(cls) -> PreferenceFeedback:
        return cls(events=0, missions={}, tags={})

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PreferenceFeedback:
        expected = {"schema_version", "events", "missions", "tags"}
        unknown = set(raw) - expected
        missing = expected - set(raw)
        if unknown:
            raise ValueError(f"unknown feedback fields: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing feedback fields: {', '.join(sorted(missing))}")
        if raw["schema_version"] != FEEDBACK_SCHEMA_VERSION:
            raise ValueError(
                "unsupported feedback schema version: "
                f"{raw['schema_version']} (expected {FEEDBACK_SCHEMA_VERSION})"
            )
        events = raw["events"]
        if isinstance(events, bool) or not isinstance(events, int) or events < 0:
            raise ValueError("feedback events must be a non-negative integer")
        return cls(
            events=events,
            missions=_validated_scores(raw["missions"], "missions"),
            tags=_validated_scores(raw["tags"], "tags"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": FEEDBACK_SCHEMA_VERSION,
            "events": self.events,
            "missions": dict(sorted(self.missions.items())),
            "tags": dict(sorted(self.tags.items())),
        }


def load_feedback(path: Path) -> PreferenceFeedback:
    if not path.exists():
        return PreferenceFeedback.empty()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("feedback state must contain a JSON object")
    return PreferenceFeedback.from_dict(raw)


def save_feedback(path: Path, feedback: PreferenceFeedback) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(feedback.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _updated_score(scores: dict[str, int], key: str, delta: int) -> dict[str, int]:
    updated = dict(scores)
    value = _clamp(updated.get(key, 0) + delta)
    if value:
        updated[key] = value
    else:
        updated.pop(key, None)
    return updated


def record_feedback(
    path: Path,
    *,
    mission_id: str,
    tags: Iterable[str],
    sentiment: str,
    include_tags: bool = True,
) -> PreferenceFeedback:
    mission_key = mission_id.strip()
    if not mission_key:
        raise ValueError("mission id must be a non-empty string")

    sentiment_key = sentiment.strip().casefold()
    try:
        delta = _SENTIMENT_DELTAS[sentiment_key]
    except KeyError as exc:
        allowed = ", ".join(sorted(_SENTIMENT_DELTAS))
        raise ValueError(f"feedback sentiment must be one of: {allowed}") from exc

    feedback = load_feedback(path)
    missions = _updated_score(feedback.missions, mission_key, delta)
    tag_scores = dict(feedback.tags)
    if include_tags:
        seen: set[str] = set()
        for raw_tag in tags:
            tag = normalized_label(raw_tag)
            if not tag or tag in seen:
                continue
            seen.add(tag)
            tag_scores = _updated_score(tag_scores, tag, delta)

    updated = PreferenceFeedback(
        events=feedback.events + 1,
        missions=missions,
        tags=tag_scores,
    )
    save_feedback(path, updated)
    return updated


def feedback_adjustment(
    mission_id: str,
    tags: Iterable[str],
    feedback: PreferenceFeedback | None,
) -> float:
    if feedback is None:
        return 0.0

    direct = feedback.missions.get(mission_id, 0)
    values = [
        feedback.tags.get(tag, 0)
        for raw_tag in tags
        if (tag := normalized_label(raw_tag))
    ]
    tag_signal = sum(values) / len(values) if values else 0.0
    adjustment = direct * 0.25 + tag_signal * 0.15
    return round(max(-2.0, min(2.0, adjustment)), 2)
