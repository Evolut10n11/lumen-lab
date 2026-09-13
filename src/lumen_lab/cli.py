from __future__ import annotations

import argparse
from pathlib import Path

from .ledger import Outcome, mean_absolute_calibration_error
from .models import Experiment
from .planner import choose_next, ranked
from .store import LabStore


def _store() -> LabStore:
    return LabStore(Path.cwd())


def _seed_experiments() -> list[Experiment]:
    return [
        Experiment(
            id="exp-001",
            title="GitHub Issues bridge",
            hypothesis=(
                "Mirroring the internal backlog to GitHub Issues will make autonomous "
                "work visible and steerable."
            ),
            impact=8,
            learning=7,
            feasibility=8,
            novelty=5,
            risk=2,
        ),
        Experiment(
            id="exp-002",
            title="Optional LLM planner adapter",
            hypothesis=(
                "A provider-neutral LLM adapter can improve idea generation without "
                "making secrets mandatory."
            ),
            impact=9,
            learning=9,
            feasibility=5,
            novelty=7,
            risk=5,
        ),
        Experiment(
            id="exp-003",
            title="Experiment benchmark ledger",
            hypothesis=(
                "Tracking expected versus observed outcomes will improve future "
                "prioritization decisions."
            ),
            impact=8,
            learning=9,
            feasibility=9,
            novelty=6,
            risk=1,
        ),
        Experiment(
            id="exp-004",
            title="Isolated experiment sandbox",
            hypothesis=(
                "A constrained subprocess sandbox will let experiments execute while "
                "keeping side effects explicit."
            ),
            impact=9,
            learning=8,
            feasibility=6,
            novelty=8,
            risk=7,
        ),
    ]


def cmd_seed(_: argparse.Namespace) -> int:
    store = _store()
    experiments = store.load()
    if experiments:
        print(f"Backlog already contains {len(experiments)} experiment(s); nothing changed.")
        return 0
    experiments = _seed_experiments()
    store.save(experiments)
    store.append_journal("Lab seeded", f"Created {len(experiments)} initial experiments.")
    print(f"Seeded {len(experiments)} experiments.")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    experiments = _store().load()
    if not experiments:
        print("Backlog is empty. Run `lumen seed`.")
        return 0
    print("ID       SCORE  STATUS    TITLE")
    print("-------- ------ --------- ----------------------------------------")
    ordered = sorted(
        experiments,
        key=lambda value: (value.status, -value.score(), value.id),
    )
    for item in ordered:
        print(f"{item.id:<8} {item.score():>6.2f} {item.status:<9} {item.title}")
    return 0


def cmd_next(_: argparse.Namespace) -> int:
    store = _store()
    experiments = store.load()
    active = [item for item in experiments if item.status == "active"]
    if active:
        current = sorted(active, key=lambda item: item.id)[0]
        print(f"Active: {current.id} — {current.title} (score {current.score():.2f})")
        return 0

    selected = choose_next(experiments)
    if selected is None:
        print("No backlog experiment is available.")
        return 0

    selected.status = "active"
    store.save(experiments)
    activation = (
        f"Selected **{selected.id} — {selected.title}** with priority score "
        f"{selected.score():.2f}.\n\nHypothesis: {selected.hypothesis}"
    )
    store.append_journal("Experiment activated", activation)
    print(f"Activated: {selected.id} — {selected.title} (score {selected.score():.2f})")
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    store = _store()
    experiments = store.load()
    selected = next((item for item in experiments if item.id == args.id), None)
    if selected is None:
        raise SystemExit(f"Unknown experiment id: {args.id}")
    if selected.status == "done":
        raise SystemExit(f"Experiment already completed: {args.id}")

    result = args.result.strip() or "Completed without an additional result note."
    outcome = Outcome(
        experiment_id=selected.id,
        expected_score=selected.score(),
        observed_value=args.value,
        learning_value=args.learning,
        result=result,
    )
    store.record_outcome(outcome)

    selected.status = "done"
    store.save(experiments)
    entry = (
        f"**{selected.id} — {selected.title}**\n\n{result}\n\n"
        f"Observed score: {outcome.observed_score():.2f}; "
        f"calibration error: {outcome.calibration_error():.2f}."
    )
    store.append_journal("Experiment completed", entry)
    print(f"Completed: {selected.id} — {selected.title}")
    return 0


def cmd_ledger(_: argparse.Namespace) -> int:
    outcomes = _store().load_outcomes()
    if not outcomes:
        print("Outcome ledger is empty.")
        return 0

    print("EXPERIMENT  EXPECTED  OBSERVED  ERROR  RESULT")
    print("----------  --------  --------  -----  ------------------------------")
    for outcome in outcomes:
        print(
            f"{outcome.experiment_id:<10}  {outcome.expected_score:>8.2f}  "
            f"{outcome.observed_score():>8.2f}  {outcome.calibration_error():>5.2f}  "
            f"{outcome.result}"
        )
    error = mean_absolute_calibration_error(outcomes)
    print(f"\nMean absolute calibration error: {error:.2f}")
    return 0


def cmd_journal(args: argparse.Namespace) -> int:
    _store().append_journal(args.title, args.body)
    print("Journal entry appended.")
    return 0


def cmd_pulse(_: argparse.Namespace) -> int:
    store = _store()
    experiments = store.load()
    outcomes = store.load_outcomes()
    statuses = ("backlog", "active", "done", "dropped")
    counts = {
        status: sum(item.status == status for item in experiments)
        for status in statuses
    }
    calibration_error = mean_absolute_calibration_error(outcomes)
    calibration_text = "n/a" if calibration_error is None else f"{calibration_error:.2f}"
    ordered = ranked(experiments)
    lines = [
        "# Lumen Pulse",
        "",
        "This file is generated from the current lab state.",
        "",
        f"- Backlog: {counts['backlog']}",
        f"- Active: {counts['active']}",
        f"- Done: {counts['done']}",
        f"- Dropped: {counts['dropped']}",
        f"- Calibration MAE: {calibration_text}",
        "",
        "## Ranked backlog",
        "",
    ]
    if ordered:
        lines.extend(
            f"- `{item.id}` — {item.title} — score `{item.score():.2f}`"
            for item in ordered
        )
    else:
        lines.append("No pending experiments.")
    store.state_dir.mkdir(parents=True, exist_ok=True)
    pulse_path = store.state_dir / "PULSE.md"
    pulse_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Pulse written to state/PULSE.md")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen",
        description="Operate the Lumen Lab experiment loop.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed = subparsers.add_parser("seed", help="Create the initial experiment backlog.")
    seed.set_defaults(func=cmd_seed)

    status = subparsers.add_parser("status", help="Show all experiments and their scores.")
    status.set_defaults(func=cmd_status)

    next_parser = subparsers.add_parser("next", help="Select and activate the next experiment.")
    next_parser.set_defaults(func=cmd_next)

    complete = subparsers.add_parser("complete", help="Complete and score an experiment.")
    complete.add_argument("id")
    complete.add_argument("--value", type=int, required=True, choices=range(1, 11))
    complete.add_argument("--learning", type=int, required=True, choices=range(1, 11))
    complete.add_argument("--result", default="")
    complete.set_defaults(func=cmd_complete)

    ledger = subparsers.add_parser("ledger", help="Show experiment calibration outcomes.")
    ledger.set_defaults(func=cmd_ledger)

    journal = subparsers.add_parser("journal", help="Append a manual lab journal entry.")
    journal.add_argument("title")
    journal.add_argument("body")
    journal.set_defaults(func=cmd_journal)

    pulse = subparsers.add_parser("pulse", help="Write a compact state snapshot.")
    pulse.set_defaults(func=cmd_pulse)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
