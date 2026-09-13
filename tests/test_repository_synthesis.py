from __future__ import annotations

import json
from pathlib import Path

from lumen_lab.ledger import Outcome
from lumen_lab.models import Experiment
from lumen_lab.synthesis import render_synthesis


def test_repository_synthesis_matches_state() -> None:
    root = Path(__file__).resolve().parents[1]
    state = root / "state"
    experiments = [
        Experiment.from_dict(item)
        for item in json.loads((state / "backlog.json").read_text(encoding="utf-8"))
    ]
    outcomes = [
        Outcome.from_dict(item)
        for item in json.loads((state / "outcomes.json").read_text(encoding="utf-8"))
    ]
    journal = (state / "journal.md").read_text(encoding="utf-8")
    actual = (state / "SYNTHESIS.md").read_text(encoding="utf-8")

    assert actual == render_synthesis(experiments, outcomes, journal)
