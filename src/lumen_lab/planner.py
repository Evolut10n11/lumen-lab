from __future__ import annotations

from collections.abc import Iterable

from .models import Experiment


def ranked(experiments: Iterable[Experiment]) -> list[Experiment]:
    candidates = [item for item in experiments if item.status == "backlog"]
    return sorted(candidates, key=lambda item: (-item.score(), item.id))


def choose_next(experiments: Iterable[Experiment]) -> Experiment | None:
    ordered = ranked(experiments)
    return ordered[0] if ordered else None
