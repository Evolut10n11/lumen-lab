from __future__ import annotations

import argparse
import json
from pathlib import Path

from .personalization import build_profile, initialize_workspace, profile_payload
from .profile import POLICY_MODES, load_profile, normalized_label
from .workspace import UserWorkspace


def _priority(value: str) -> tuple[str, int]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("priority must use NAME=WEIGHT, for example career=10")
    name, raw_weight = value.rsplit("=", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError("priority name must not be empty")
    try:
        weight = int(raw_weight)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("priority weight must be an integer from 1 to 10") from exc
    if not 1 <= weight <= 10:
        raise argparse.ArgumentTypeError("priority weight must be an integer from 1 to 10")
    return name, weight


def _priority_map(items: list[tuple[str, int]]) -> dict[str, int]:
    priorities: dict[str, int] = {}
    seen: set[str] = set()
    for name, weight in items:
        key = normalized_label(name)
        if key in seen:
            raise ValueError(f"duplicate priority: {name}")
        seen.add(key)
        priorities[name] = weight
    return priorities


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen-user",
        description="Create and inspect isolated local user profiles for personalized Lumen behavior.",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--user",
        help="Local user id. Defaults to LUMEN_USER_ID or 'default'.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create personalized local state from explicit inputs.")
    init.add_argument("--name", required=True, help="Display name for this local profile.")
    init.add_argument(
        "--priority",
        type=_priority,
        action="append",
        required=True,
        metavar="NAME=WEIGHT",
        help="Priority and weight from 1 to 10. Repeat for multiple priorities.",
    )
    init.add_argument("--skill", action="append", default=[])
    init.add_argument("--interest", action="append", default=[])
    init.add_argument("--constraint", action="append", default=[])
    init.add_argument("--stack", action="append", default=[])
    init.add_argument("--risk-tolerance", type=int, choices=range(1, 11), default=5)
    init.add_argument("--mode", choices=sorted(POLICY_MODES), default="reviewed")
    init.add_argument("--allow-llm", action="store_true")
    init.add_argument("--max-candidates", type=int, choices=range(1, 21), default=5)
    init.add_argument(
        "--replace",
        action="store_true",
        help="Explicitly replace an existing profile, missions and work templates.",
    )
    init.add_argument("--json", action="store_true")

    show = subparsers.add_parser("show", help="Show the resolved local user profile.")
    show.add_argument("--json", action="store_true")

    subparsers.add_parser("path", help="Print the resolved local workspace path.")
    subparsers.add_parser("list", help="List initialized local users under this repository.")
    return parser


def _init(args: argparse.Namespace, workspace: UserWorkspace) -> int:
    profile = build_profile(
        user_id=workspace.user_id,
        display_name=args.name,
        priorities=_priority_map(args.priority),
        skills=args.skill,
        interests=args.interest,
        constraints=args.constraint,
        preferred_stack=args.stack,
        risk_tolerance=args.risk_tolerance,
        policy_mode=args.mode,
        allow_llm=args.allow_llm,
        max_candidates=args.max_candidates,
    )
    missions, sessions = initialize_workspace(workspace, profile, replace=args.replace)
    if args.json:
        print(
            json.dumps(
                {
                    "user_id": workspace.user_id,
                    "workspace": str(workspace.directory),
                    "profile": profile_payload(profile),
                    "missions_created": len(missions),
                    "work_sessions_created": len(sessions),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    print(f"Initialized Lumen user: {profile.display_name} [{workspace.user_id}]")
    print(f"Workspace: {workspace.directory}")
    print(f"Personalized missions: {len(missions)}")
    print("Next: run `lumen-radar` or `lumen-work` with the same --user value.")
    return 0


def _show(args: argparse.Namespace, workspace: UserWorkspace) -> int:
    workspace.require_initialized()
    profile = load_profile(workspace.profile_path)
    payload = profile_payload(profile)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(f"{profile.display_name} [{profile.id}]")
    print("Priorities:")
    for name, weight in sorted(
        profile.priorities.items(),
        key=lambda item: (-item[1], normalized_label(item[0])),
    ):
        print(f"  {weight}/10  {name}")
    if profile.interests:
        print(f"Interests: {', '.join(profile.interests)}")
    if profile.skills:
        print(f"Skills: {', '.join(profile.skills)}")
    if profile.constraints:
        print(f"Constraints: {', '.join(profile.constraints)}")
    return 0


def _list_users(root: Path) -> int:
    users_root = root / ".lumen" / "users"
    if not users_root.exists():
        print("No initialized local users.")
        return 0
    found = False
    for directory in sorted(path for path in users_root.iterdir() if path.is_dir()):
        profile_path = directory / "profile.json"
        if not profile_path.is_file():
            continue
        found = True
        try:
            profile = load_profile(profile_path)
        except (OSError, json.JSONDecodeError, ValueError):
            print(f"{directory.name}: invalid profile")
            continue
        print(f"{directory.name}: {profile.display_name}")
    if not found:
        print("No initialized local users.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = UserWorkspace.from_root(args.root, args.user)
    try:
        if args.command == "init":
            return _init(args, workspace)
        if args.command == "show":
            return _show(args, workspace)
        if args.command == "path":
            print(workspace.directory)
            return 0
        if args.command == "list":
            return _list_users(args.root)
        raise ValueError(f"unknown command: {args.command}")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"user error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
