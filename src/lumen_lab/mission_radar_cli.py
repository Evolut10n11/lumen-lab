from __future__ import annotations

import argparse
import json
from pathlib import Path

from .mission_radar import DEFAULT_MISSIONS_PATH, load_missions, radar_snapshot
from .profile import DEFAULT_PROFILE_PATH, load_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen-radar",
        description="Rank user or project missions and show the most valuable next action.",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_MISSIONS_PATH,
        help="Mission state JSON file (default: state/missions.json).",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE_PATH,
        help="Explicit local profile JSON (default: state/profile.json when present).",
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
        profile = load_profile(args.profile) if args.profile.exists() else None
        snapshot = radar_snapshot(missions, top=args.top, profile=profile)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"mission radar error: {exc}")
        return 2

    if args.json:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0

    if not snapshot:
        print("No active missions.")
        return 0

    print("Lumen Mission Radar")
    if profile is not None:
        print(f"Profile: {profile.display_name} [{profile.id}]")
    for index, mission in enumerate(snapshot, start=1):
        score_text = f"score {mission['score']:.2f}"
        if mission["score"] != mission["base_score"]:
            score_text += f" (base {mission['base_score']:.2f})"
        print(f"{index}. {mission['title']} [{mission['id']}] — {score_text}")
        print(f"   Why now: {mission['why_now']}")
        print(f"   Next action: {mission['next_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
