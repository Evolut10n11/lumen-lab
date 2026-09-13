from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_PROFILE_PATH = Path("state/profile.json")
POLICY_MODES = {"disabled", "reviewed", "optional-llm"}


def normalized_label(value: str) -> str:
    return value.strip().casefold()


def _validated_labels(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"profile {name} must be a JSON list")
    labels: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"profile {name} must contain non-empty strings")
        normalized = normalized_label(item)
        if normalized in seen:
            raise ValueError(f"profile {name} contains duplicate value: {item.strip()}")
        seen.add(normalized)
        labels.append(item.strip())
    return tuple(labels)


@dataclass(frozen=True, slots=True)
class CandidateGenerationPolicy:
    mode: str
    allow_llm: bool
    max_candidates: int

    @classmethod
    def from_dict(cls, raw: object) -> CandidateGenerationPolicy:
        if not isinstance(raw, dict):
            raise ValueError("candidate_generation_policy must be a JSON object")
        expected = {"mode", "allow_llm", "max_candidates"}
        unknown = set(raw) - expected
        missing = expected - set(raw)
        if unknown:
            raise ValueError(f"unknown candidate policy fields: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing candidate policy fields: {', '.join(sorted(missing))}")
        policy = cls(**raw)
        policy.validate()
        return policy

    def validate(self) -> None:
        if self.mode not in POLICY_MODES:
            allowed = ", ".join(sorted(POLICY_MODES))
            raise ValueError(f"candidate policy mode must be one of: {allowed}")
        if not isinstance(self.allow_llm, bool):
            raise ValueError("candidate policy allow_llm must be boolean")
        if isinstance(self.max_candidates, bool) or not isinstance(self.max_candidates, int):
            raise ValueError("candidate policy max_candidates must be an integer")
        if not 1 <= self.max_candidates <= 20:
            raise ValueError("candidate policy max_candidates must be between 1 and 20")
        if self.allow_llm and self.mode != "optional-llm":
            raise ValueError("candidate policy allow_llm requires mode optional-llm")


@dataclass(frozen=True, slots=True)
class Profile:
    id: str
    display_name: str
    priorities: dict[str, int]
    skills: tuple[str, ...]
    interests: tuple[str, ...]
    constraints: tuple[str, ...]
    preferred_stack: tuple[str, ...]
    risk_tolerance: int
    candidate_generation_policy: CandidateGenerationPolicy

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Profile:
        expected = {
            "id",
            "display_name",
            "priorities",
            "skills",
            "interests",
            "constraints",
            "preferred_stack",
            "risk_tolerance",
            "candidate_generation_policy",
        }
        unknown = set(raw) - expected
        missing = expected - set(raw)
        if unknown:
            raise ValueError(f"unknown profile fields: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing profile fields: {', '.join(sorted(missing))}")

        priorities_raw = raw["priorities"]
        if not isinstance(priorities_raw, dict):
            raise ValueError("profile priorities must be a JSON object")
        priorities: dict[str, int] = {}
        normalized_keys: set[str] = set()
        for key, weight in priorities_raw.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("profile priority names must be non-empty strings")
            normalized = normalized_label(key)
            if normalized in normalized_keys:
                raise ValueError(f"profile priorities contain duplicate key: {key.strip()}")
            if isinstance(weight, bool) or not isinstance(weight, int) or not 1 <= weight <= 10:
                raise ValueError(f"profile priority {key.strip()} must be an integer from 1 to 10")
            normalized_keys.add(normalized)
            priorities[key.strip()] = weight

        profile = cls(
            id=raw["id"],
            display_name=raw["display_name"],
            priorities=priorities,
            skills=_validated_labels(raw["skills"], "skills"),
            interests=_validated_labels(raw["interests"], "interests"),
            constraints=_validated_labels(raw["constraints"], "constraints"),
            preferred_stack=_validated_labels(raw["preferred_stack"], "preferred_stack"),
            risk_tolerance=raw["risk_tolerance"],
            candidate_generation_policy=CandidateGenerationPolicy.from_dict(
                raw["candidate_generation_policy"]
            ),
        )
        profile.validate()
        return profile

    def validate(self) -> None:
        for name in ("id", "display_name"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"profile {name} must be a non-empty string")
        if isinstance(self.risk_tolerance, bool) or not isinstance(self.risk_tolerance, int):
            raise ValueError("profile risk_tolerance must be an integer")
        if not 1 <= self.risk_tolerance <= 10:
            raise ValueError("profile risk_tolerance must be between 1 and 10")

    def priority_for(self, tag: str) -> int | None:
        normalized = normalized_label(tag)
        for key, value in self.priorities.items():
            if normalized_label(key) == normalized:
                return value
        return None


def load_profile(path: Path = DEFAULT_PROFILE_PATH) -> Profile:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("profile state must contain a JSON object")
    return Profile.from_dict(raw)
