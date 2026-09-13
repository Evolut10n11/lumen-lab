from __future__ import annotations

import json
from pathlib import Path

import pytest

from lumen_lab.ledger import Outcome
from lumen_lab.models import Experiment
from lumen_lab.provenance import (
    ProvenanceRecord,
    load_provenance,
    provenance_snapshot,
    validate_provenance,
)
from lumen_lab.provenance_cli import main


def experiment(experiment_id: str = "exp-001", status: str = "done") -> Experiment:
    return Experiment(experiment_id, "Example", "Hypothesis", 8, 8, 8, 6, 1, status)


def outcome(experiment_id: str = "exp-001") -> Outcome:
    return Outcome(experiment_id, 7.5, 8, 9, "Delivered deterministic evidence.")


def test_record_rejects_unsafe_and_duplicate_artifacts() -> None:
    with pytest.raises(ValueError, match="unsafe provenance artifact path"):
        ProvenanceRecord("exp-001", ("../secret",)).validate()
    with pytest.raises(ValueError, match="forward slashes"):
        ProvenanceRecord("exp-001", ("docs\\file.md",)).validate()
    with pytest.raises(ValueError, match="duplicate provenance artifact"):
        ProvenanceRecord("exp-001", ("docs/file.md", "docs/file.md")).validate()


def test_load_rejects_duplicate_experiment_ids(tmp_path: Path) -> None:
    path = tmp_path / "provenance.json"
    path.write_text(
        json.dumps(
            [
                {"experiment_id": "exp-001", "artifacts": ["a.txt"]},
                {"experiment_id": "exp-001", "artifacts": ["b.txt"]},
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate provenance experiment_id"):
        load_provenance(path)


def test_validate_requires_complete_coverage_and_existing_files(tmp_path: Path) -> None:
    (tmp_path / "evidence.txt").write_text("ok", encoding="utf-8")
    experiments = [experiment("exp-001"), experiment("exp-002")]
    outcomes = [outcome("exp-001"), outcome("exp-002")]
    records = [ProvenanceRecord("exp-001", ("evidence.txt",))]
    with pytest.raises(ValueError, match="completed experiments missing provenance: exp-002"):
        validate_provenance(tmp_path, experiments, outcomes, records)

    records.append(ProvenanceRecord("exp-002", ("missing.txt",)))
    with pytest.raises(ValueError, match="provenance artifact does not exist"):
        validate_provenance(tmp_path, experiments, outcomes, records)


def test_validate_rejects_non_completed_record(tmp_path: Path) -> None:
    (tmp_path / "evidence.txt").write_text("ok", encoding="utf-8")
    experiments = [experiment("exp-001", "backlog")]
    records = [ProvenanceRecord("exp-001", ("evidence.txt",))]
    with pytest.raises(ValueError, match="non-completed experiments"):
        validate_provenance(tmp_path, experiments, [], records)


def test_snapshot_is_sorted_filterable_and_reports_journal() -> None:
    experiments = [experiment("exp-002"), experiment("exp-001")]
    outcomes = [outcome("exp-002"), outcome("exp-001")]
    records = [
        ProvenanceRecord("exp-002", ("b.txt",)),
        ProvenanceRecord("exp-001", ("a.txt",)),
    ]
    journal = "## 2026-09-13 — exp-001 completed\n"
    snapshot = provenance_snapshot(experiments, outcomes, records, journal)
    assert [item["experiment_id"] for item in snapshot] == ["exp-001", "exp-002"]
    assert snapshot[0]["journal_section"] is True
    assert snapshot[1]["journal_section"] is False
    assert provenance_snapshot(experiments, outcomes, records, journal, "exp-002")[0][
        "experiment_id"
    ] == "exp-002"
    with pytest.raises(ValueError, match="provenance experiment not found"):
        provenance_snapshot(experiments, outcomes, records, journal, "exp-999")


def _write_repo(root: Path) -> None:
    state = root / "state"
    state.mkdir()
    (root / "evidence.txt").write_text("ok", encoding="utf-8")
    (state / "backlog.json").write_text(
        json.dumps([experiment().to_dict()]), encoding="utf-8"
    )
    (state / "outcomes.json").write_text(
        json.dumps([outcome().to_dict()]), encoding="utf-8"
    )
    (state / "provenance.json").write_text(
        json.dumps([{"experiment_id": "exp-001", "artifacts": ["evidence.txt"]}]),
        encoding="utf-8",
    )
    (state / "journal.md").write_text(
        "## 2026-09-13 — exp-001 completed\n", encoding="utf-8"
    )


def test_cli_json_and_filter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_repo(tmp_path)
    assert main(["--root", str(tmp_path), "--experiment", "exp-001", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["experiment_id"] == "exp-001"
    assert payload[0]["artifacts"] == ["evidence.txt"]


def test_cli_is_read_only(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_repo(tmp_path)
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert main(["--root", str(tmp_path)]) == 0
    capsys.readouterr()
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*"))
    assert after == before


def test_real_repository_provenance_is_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    raw_experiments = json.loads((root / "state/backlog.json").read_text(encoding="utf-8"))
    raw_outcomes = json.loads((root / "state/outcomes.json").read_text(encoding="utf-8"))
    experiments = [Experiment.from_dict(item) for item in raw_experiments]
    outcomes = [Outcome.from_dict(item) for item in raw_outcomes]
    records = load_provenance(root / "state/provenance.json")
    validate_provenance(root, experiments, outcomes, records)
