from __future__ import annotations

import argparse
import json
from pathlib import Path

from .mission_radar import load_missions
from .profile import load_profile
from .work_session import (
    choose_mission,
    load_progress,
    load_templates,
    mark_step_done,
    session_snapshot,
    template_for,
)
from .workspace import UserWorkspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen-work",
        description="Turn the current user's top mission into a concrete focused work session.",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--user",
        help="Local user id. Defaults to LUMEN_USER_ID or 'default'.",
    )
    parser.add_argument(
        "--mission",
        help="Use a specific active mission instead of the current top-ranked mission.",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        help="Explicit profile JSON. By default uses this user's isolated local profile.",
    )
    parser.add_argument(
        "--done",
        type=int,
        help="Mark one step number complete in this user's local progress state.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )
    parser.add_argument("--missions", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--templates", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--progress", type=Path, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = UserWorkspace.from_root(args.root, args.user)
    try:
        if args.missions is None or args.templates is None:
            workspace.require_initialized()

        missions_path = args.missions or workspace.missions_path
        templates_path = args.templates or workspace.work_sessions_path
        progress_path = args.progress or workspace.work_progress_path
        profile_path = args.profile or workspace.profile_path

        missions = load_missions(missions_path)
        templates = load_templates(templates_path)
        profile = load_profile(profile_path) if profile_path.exists() else None
        mission = choose_mission(missions, args.mission, profile)
        template = template_for(templates, mission.id)

        progress = load_progress(progress_path)
        if args.done is not None:
            progress = mark_step_done(
                progress_path,
                mission.id,
                args.done,
                len(template.steps),
            )
        snapshot = session_snapshot(mission, template, progress, profile)
        snapshot["user_id"] = workspace.user_id if profile is not None else None
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
        print(
            "Mark progress with: "
            f"lumen-work --user {workspace.user_id} --done <step-number>"
        )
    else:
        print("Session complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
