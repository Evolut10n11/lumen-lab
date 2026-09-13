from pathlib import Path

from lumen_lab.models import Experiment
from lumen_lab.store import LabStore


def test_store_round_trip(tmp_path: Path) -> None:
    store = LabStore(tmp_path)
    experiment = Experiment(
        id="exp-test",
        title="Persistence test",
        hypothesis="State survives a save/load cycle.",
        impact=7,
        learning=7,
        feasibility=9,
        novelty=4,
        risk=1,
    )

    store.save([experiment])
    loaded = store.load()

    assert loaded == [experiment]


def test_journal_append_creates_entry(tmp_path: Path) -> None:
    store = LabStore(tmp_path)
    store.append_journal("Observation", "A concrete result.")

    journal = (tmp_path / "state" / "journal.md").read_text(encoding="utf-8")
    assert "# Lab Journal" in journal
    assert "Observation" in journal
    assert "A concrete result." in journal
