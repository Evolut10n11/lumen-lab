from __future__ import annotations

import argparse
import json
from pathlib import Path

from .app_service import LumenApplication


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen-dashboard",
        description="Show the user-scoped application view used by future GUI clients.",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--user",
        help="Local user id. Defaults to LUMEN_USER_ID or 'default'.",
    )
    parser.add_argument("--top", type=int, default=3)
    parser.add_argument(
        "--done",
        type=int,
        help="Complete one step on the current top mission before rendering the dashboard.",
    )
    parser.add_argument("--mission", help="Mission id used together with --done.")
    parser.add_argument("--json", action="store_true")
    return parser


def _render_human(payload: dict[str, object]) -> None:
    user = payload["user"]
    today = payload["today"]
    summary = payload["summary"]
    radar = payload["radar"]

    if not isinstance(user, dict) or not isinstance(summary, dict) or not isinstance(radar, list):
        raise ValueError("invalid dashboard payload")

    print(f"Lumen — {user['display_name']}")
    print(
        f"Active missions: {summary['active_missions']} | "
        "Active progress: "
        f"{summary['completed_active_steps']}/{summary['total_active_steps']} steps | "
        f"All-time steps: {summary['completed_steps']}"
    )
    if isinstance(today, dict):
        print("")
        print(f"Today: {today['title']}")
        print(f"Why now: {today['why_now']}")
        selection = today.get("selection")
        if isinstance(selection, dict):
            reasons = selection.get("reasons")
            if isinstance(reasons, list):
                for reason in reasons:
                    print(f"  - {reason}")
        progress = today.get("progress")
        if isinstance(progress, dict):
            print(
                f"Session progress: {progress['completed']}/{progress['total']} "
                f"({progress['percent']}%)"
            )
    else:
        print("Today: no active mission")

    print("")
    print("Radar:")
    for index, mission in enumerate(radar, start=1):
        if not isinstance(mission, dict):
            continue
        print(f"  {index}. {mission['title']} — {mission['score']:.2f}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    app = LumenApplication(args.root)
    try:
        if args.done is not None:
            app.complete_step(args.done, args.user, mission_id=args.mission)
        payload = app.dashboard(args.user, top=args.top)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"dashboard error: {exc}")
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    _render_human(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
