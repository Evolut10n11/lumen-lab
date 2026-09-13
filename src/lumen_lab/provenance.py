from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .ledger import Outcome
from .models import Experiment

DEFAULT_PROVENANCE_PATH = Path("state/provenance.json")


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    experiment_id: str
    artifacts: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ProvenanceRecord:
        expected = {"experiment_id", "artifacts"}
        unknown = set(raw) - expected
        missing = expected - set(raw)
        if unknown:
            raise ValueError(f"unknown provenance fields: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing provenance fields: {', '.join(sorted(missing))}")
        artifacts = raw["artifacts"]
        if not isinstance(artifacts, list):
            raise ValueError("provenance artifacts must be a JSON list")
        record = cls(raw["experiment_id"], tuple(artifacts))
        record.validate()
        return record

    def validate(self) -> None:
        if not isinstance(self.experiment_id, str) or not self.experiment_id.strip():
            raise ValueError("provenance experiment_id must be a non-empty string")
        if not self.artifacts:
            raise ValueError(f"provenance {self.experiment_id} must contain at least one artifact")
        seen: set[str] = set()
        for artifact in self.artifacts:
            if not isinstance(artifact, str) or not artifact.strip():
                raise ValueError("provenance artifacts must be non-empty strings")
            path = PurePosixPath(artifact)
            if path.is_absolute() or ".." in path.parts or artifact.startswith(("./", ".\\")):
                raise ValueError(f"unsafe provenance artifact path: {artifact}")
            if "\\" in artifact:
                raise ValueError(f"provenance paths must use forward slashes: {artifact}")
            if artifact in seen:
                raise ValueError(
                    f"duplicate provenance artifact for {self.experiment_id}: {artifact}"
                )
            seen.add(artifact)


def load_provenance(path: Path = DEFAULT_PROVENANCE_PATH) -> list[ProvenanceRecord]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("provenance state must contain a JSON list")
    records: list[ProvenanceRecord] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("provenance entries must be JSON objects")
        record = ProvenanceRecord.from_dict(item)
        if record.experiment_id in seen:
            raise ValueError(f"duplicate provenance experiment_id: {record.experiment_id}")
        seen.add(record.experiment_id)
        records.append(record)
    return records


def validate_provenance(
    root: Path,
    experiments: list[Experiment],
    outcomes: list[Outcome],
    records: list[ProvenanceRecord],
) -> None:
    experiments_by_id = {item.id: item for item in experiments}
    outcome_ids = {item.experiment_id for item in outcomes}
    record_ids = {item.experiment_id for item in records}
    completed_ids = {item.id for item in experiments if item.status == "done"}

    unknown = sorted(record_ids - completed_ids)
    if unknown:
        raise ValueError(f"provenance references non-completed experiments: {', '.join(unknown)}")
    missing = sorted(completed_ids - record_ids)
    if missing:
        raise ValueError(f"completed experiments missing provenance: {', '.join(missing)}")
    missing_outcomes = sorted(completed_ids - outcome_ids)
    if missing_outcomes:
        raise ValueError(f"completed experiments missing outcomes: {', '.join(missing_outcomes)}")

    for record in records:
        if record.experiment_id not in experiments_by_id:
            raise ValueError(f"unknown provenance experiment: {record.experiment_id}")
        for artifact in record.artifacts:
            if not (root / Path(*PurePosixPath(artifact).parts)).is_file():
                raise ValueError(
                    f"provenance artifact does not exist for {record.experiment_id}: {artifact}"
                )


def journal_has_section(journal_text: str, experiment_id: str) -> bool:
    return any(
        line.startswith("## ") and experiment_id in line
        for line in journal_text.splitlines()
    )


def provenance_snapshot(
    experiments: list[Experiment],
    outcomes: list[Outcome],
    records: list[ProvenanceRecord],
    journal_text: str,
    experiment_id: str | None = None,
) -> list[dict[str, Any]]:
    experiment_by_id = {item.id: item for item in experiments}
    outcome_by_id = {item.experiment_id: item for item in outcomes}
    selected = sorted(records, key=lambda item: item.experiment_id)
    if experiment_id is not None:
        selected = [item for item in selected if item.experiment_id == experiment_id]
        if not selected:
            raise ValueError(f"provenance experiment not found: {experiment_id}")

    return [
        {
            "experiment_id": record.experiment_id,
            "title": experiment_by_id[record.experiment_id].title,
            "outcome": outcome_by_id[record.experiment_id].result,
            "journal_section": journal_has_section(journal_text, record.experiment_id),
            "artifacts": list(record.artifacts),
        }
        for record in selected
    ]
