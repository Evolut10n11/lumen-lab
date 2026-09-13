from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ledger import Outcome
from .models import Experiment
from .provenance import load_provenance, provenance_snapshot, validate_provenance


def _load_list(path: Path) -> list[object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path} must contain a JSON list")
    return raw


def _load_experiments(path: Path) -> list[Experiment]:
    result: list[Experiment] = []
    for item in _load_list(path):
        if not isinstance(item, dict):
            raise ValueError("backlog entries must be JSON objects")
        result.append(Experiment.from_dict(item))
    return result


def _load_outcomes(path: Path) -> list[Outcome]:
    result: list[Outcome] = []
    for item in _load_list(path):
        if not isinstance(item, dict):
            raise ValueError("outcome entries must be JSON objects")
        result.append(Outcome.from_dict(item))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen-provenance",
        description="Inspect deterministic evidence links for completed Lumen experiments.",
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--experiment", help="Show one experiment ID only.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root
    state = root / "state"
    try:
        experiments = _load_experiments(state / "backlog.json")
        outcomes = _load_outcomes(state / "outcomes.json")
        records = load_provenance(state / "provenance.json")
        validate_provenance(root, experiments, outcomes, records)
        journal_text = (state / "journal.md").read_text(encoding="utf-8")
        snapshot = provenance_snapshot(
            experiments,
            outcomes,
            records,
            journal_text,
            experiment_id=args.experiment,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"provenance error: {exc}")
        return 2

    if args.json:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0

    print("Lumen Experiment Provenance")
    for item in snapshot:
        print(f"{item['experiment_id']} — {item['title']}")
        print(f"  Journal section: {'yes' if item['journal_section'] else 'no'}")
        print(f"  Outcome: {item['outcome']}")
        print("  Artifacts:")
        for artifact in item["artifacts"]:
            print(f"    - {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
