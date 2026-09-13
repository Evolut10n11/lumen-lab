from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .ledger import Outcome
from .models import Experiment


@dataclass(slots=True)
class LabStore:
    root: Path
    state_directory: Path | None = None

    @property
    def state_dir(self) -> Path:
        return self.state_directory if self.state_directory is not None else self.root / "state"

    @property
    def backlog_path(self) -> Path:
        return self.state_dir / "backlog.json"

    @property
    def outcomes_path(self) -> Path:
        return self.state_dir / "outcomes.json"

    @property
    def journal_path(self) -> Path:
        return self.state_dir / "journal.md"

    def ensure(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if not self.backlog_path.exists():
            self.save([])
        if not self.outcomes_path.exists():
            self.save_outcomes([])
        if not self.journal_path.exists():
            self.journal_path.write_text("# Lab Journal\n\n", encoding="utf-8")

    def load(self) -> list[Experiment]:
        self.ensure()
        raw = json.loads(self.backlog_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("backlog must contain a JSON list")
        return [Experiment.from_dict(item) for item in raw]

    def save(self, experiments: list[Experiment]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = [item.to_dict() for item in experiments]
        self.backlog_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def load_outcomes(self) -> list[Outcome]:
        self.ensure()
        raw = json.loads(self.outcomes_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError("outcomes must contain a JSON list")
        return [Outcome.from_dict(item) for item in raw]

    def save_outcomes(self, outcomes: list[Outcome]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        payload = [item.to_dict() for item in outcomes]
        self.outcomes_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def record_outcome(self, outcome: Outcome) -> None:
        outcome.validate()
        outcomes = self.load_outcomes()
        if any(item.experiment_id == outcome.experiment_id for item in outcomes):
            raise ValueError(f"outcome already recorded for {outcome.experiment_id}")
        outcomes.append(outcome)
        self.save_outcomes(outcomes)

    def append_journal(self, title: str, body: str) -> None:
        self.ensure()
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        with self.journal_path.open("a", encoding="utf-8") as stream:
            stream.write(f"## {timestamp} — {title}\n\n{body.strip()}\n\n")
