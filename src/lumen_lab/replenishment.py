from __future__ import annotations

import json
from pathlib import Path

from .models import Experiment
from .planner import ranked

DEFAULT_REGISTRY_PATH = Path("state/candidates.json")


def load_candidate_registry(path: Path = DEFAULT_REGISTRY_PATH) -> list[Experiment]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("candidate registry must contain a JSON list")

    candidates: list[Experiment] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("candidate registry entries must be JSON objects")
        candidate = Experiment.from_dict(item)
        if candidate.status != "backlog":
            raise ValueError(f"candidate {candidate.id} must have backlog status")
        if candidate.id in seen:
            raise ValueError(f"duplicate candidate id: {candidate.id}")
        seen.add(candidate.id)
        candidates.append(candidate)
    return candidates


def has_pending_work(experiments: list[Experiment]) -> bool:
    return any(item.status in {"backlog", "active"} for item in experiments)


def replenishment_candidates(
    experiments: list[Experiment],
    registry: list[Experiment] | None = None,
) -> list[Experiment]:
    if has_pending_work(experiments):
        return []

    source = load_candidate_registry() if registry is None else registry
    existing_ids = {item.id for item in experiments}
    available: list[Experiment] = []
    seen: set[str] = set()
    for template in source:
        template.validate()
        if template.status != "backlog":
            raise ValueError(f"candidate {template.id} must have backlog status")
        if template.id in seen:
            raise ValueError(f"duplicate candidate id: {template.id}")
        seen.add(template.id)
        if template.id in existing_ids:
            continue
        available.append(Experiment.from_dict(template.to_dict()))
    return ranked(available)


def apply_replenishment(
    experiments: list[Experiment],
    registry: list[Experiment] | None = None,
) -> tuple[list[Experiment], list[Experiment]]:
    candidates = replenishment_candidates(experiments, registry)
    return list(experiments) + candidates, candidates
