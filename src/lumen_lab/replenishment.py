from __future__ import annotations

from collections.abc import Iterable

from .models import Experiment


_CURATED_NEXT_GENERATION = (
    Experiment(
        id="exp-006",
        title="Planner calibration checkpoint",
        hypothesis=(
            "Five completed outcomes are enough to inspect systematic planner bias "
            "before considering any scoring-weight change."
        ),
        impact=8,
        learning=10,
        feasibility=9,
        novelty=5,
        risk=2,
    ),
    Experiment(
        id="exp-007",
        title="Sandbox capability manifests",
        hypothesis=(
            "Named capability manifests can make allowed experiment commands easier "
            "to audit without weakening the sandbox allowlist."
        ),
        impact=8,
        learning=8,
        feasibility=8,
        novelty=6,
        risk=3,
    ),
    Experiment(
        id="exp-008",
        title="Journal synthesis snapshot",
        hypothesis=(
            "A deterministic synthesis of completed experiments can surface repeated "
            "lessons and missing capabilities without making the journal less auditable."
        ),
        impact=7,
        learning=9,
        feasibility=9,
        novelty=6,
        risk=1,
    ),
)


def has_pending_work(experiments: Iterable[Experiment]) -> bool:
    return any(item.status in {"backlog", "active"} for item in experiments)


def replenishment_candidates(experiments: Iterable[Experiment]) -> list[Experiment]:
    existing = list(experiments)
    if has_pending_work(existing):
        return []

    existing_ids = {item.id for item in existing}
    candidates: list[Experiment] = []
    for template in _CURATED_NEXT_GENERATION:
        if template.id in existing_ids:
            continue
        candidate = Experiment.from_dict(template.to_dict())
        candidate.validate()
        candidates.append(candidate)
    return candidates


def apply_replenishment(
    experiments: Iterable[Experiment],
) -> tuple[list[Experiment], list[Experiment]]:
    existing = list(experiments)
    candidates = replenishment_candidates(existing)
    return existing + candidates, candidates
