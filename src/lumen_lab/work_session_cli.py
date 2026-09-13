from __future__ import annotations

import argparse
import json
from pathlib import Path

from .mission_radar import DEFAULT_MISSIONS_PATH, load_missions
from .profile import DEFAULT_PROFILE_PATH, load_profile
from .work_session import (
    DEFAULT_PROGRESS_PATH,
    DEFAULT_TEMPLATES_PATH,
    choose_mission,
    load_progress,
    load_templates,
    mark_step_done,
    session_snapshot,
    template_for,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen-work",
        description="Turn the current top mission into a concrete focused work session.",
    )
    parser.add_argument(
        "--mission",
        help="Use a specific active mission instead of the current top-ranked mission.",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE_PATH,
        help="Explicit local profile JSON (default: state/profile.json when present).",
    )
    parser.add_argument(
        "--done",
        type=int,
        help="Mark one step number complete in local runtime progress state.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    parser.add_argument(
        "--missions",
        type=Path,
        default=DEFAULT_MISSIONS_PATH,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--templates",
        type=Path,
        default=DEFAULT_TEMPLATES_PATH,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=DEFAULT_PROGRESS_PATH,
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        missions = load_missions(args.missions)
        templates = load_templates(args.templates)
        profile = load_profile(args.profile) if args.profile.exists() else None
        mission = choose_mission(missions, args.mission, profile)
        template = template_for(templates, mission.id)

        progress = load_progress(args.progress)
        if args.done is not None:
            progress = mark_step_done(
                args.progress,
                mission.id,
                args.done,
                len(template.steps),
            )
        snapshot = session_snapshot(mission, template, progress, profile)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"work session error: {exc}")
        return 2

    if args.json:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0

    progress_info = snapshot["progress"]
    print("Lumen Work Session")
    print(f"Mission: {snapshot['title']} [{snapshot['mission_id']}]")
    if snapshot["profile_id"] is not None:
        print(f"Profile: {snapshot['profile_id']}")
    print(f"Why now: {snapshot['why_now']}")
    score_text = f"{snapshot['score']:.2f}"
    if snapshot["score"] != snapshot["base_score"]:
        score_text += f" (base {snapshot['base_score']:.2f})"
    print(f"Priority score: {score_text}")
    print(f"Focus window: {snapshot['focus_minutes']} minutes")
    print(
        "Progress: "
        f"{progress_info['completed']}/{progress_info['total']} "
        f"({progress_info['percent']}%)"
    )
    print("Steps:")
    for step in snapshot["steps"]:
        marker = "x" if step["done"] else " "
        print(f"  [{marker}] {step['number']}. {step['text']}")
    print(f"Definition of Done: {snapshot['definition_of_done']}")
    if progress_info["completed"] < progress_info["total"]:
        print("Mark progress with: lumen-work --done <step-number>")
    else:
        print("Session complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
