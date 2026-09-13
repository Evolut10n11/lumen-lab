from __future__ import annotations

import argparse
import json
from pathlib import Path

from .mission_radar import DEFAULT_MISSIONS_PATH, load_missions, radar_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen-radar",
        description="Rank Elaine/user missions and show the most valuable next action.",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_MISSIONS_PATH,
        help="Mission state JSON file (default: state/missions.json).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=1,
        help="Number of active missions to show (default: 1).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        missions = load_missions(args.state)
        snapshot = radar_snapshot(missions, top=args.top)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"mission radar error: {exc}")
        return 2

    if args.json:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0

    if not snapshot:
        print("No active missions.")
        return 0

    print("Elaine Mission Radar")
    for index, mission in enumerate(snapshot, start=1):
        print(f"{index}. {mission['title']} [{mission['id']}] — score {mission['score']:.2f}")
        print(f"   Why now: {mission['why_now']}")
        print(f"   Next action: {mission['next_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
