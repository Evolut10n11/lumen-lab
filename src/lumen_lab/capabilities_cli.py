import argparse
import json
from pathlib import Path

from .capabilities import (
    CapabilityError,
    load_capability_manifests,
    render_manifest_list,
    resolve_execution_policy,
    run_with_policy,
)
from .sandbox import SandboxError


def _default_manifest_path() -> Path:
    return Path.cwd() / "state" / "capabilities.json"


def _load(path: str) -> list:
    manifest_path = Path(path) if path else _default_manifest_path()
    return load_capability_manifests(manifest_path)


def cmd_list(args: argparse.Namespace) -> int:
    try:
        manifests = _load(args.file)
    except CapabilityError as exc:
        raise SystemExit(str(exc)) from exc
    print(render_manifest_list(manifests), end="")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    argv = list(args.argv)
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        raise SystemExit("sandbox command is required after --")

    try:
        manifests = _load(args.file)
        policy = resolve_execution_policy(
            manifests,
            manifest_name=args.manifest,
            manual_allowed=tuple(args.allow),
            timeout_override=args.timeout,
            max_output_override=args.max_output_bytes,
        )
        result = run_with_policy(argv, policy)
    except (CapabilityError, SandboxError) as exc:
        raise SystemExit(str(exc)) from exc

    if args.json:
        payload = result.to_dict()
        payload["policy"] = policy.source
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        status = "TIMEOUT" if result.timed_out else f"EXIT {result.returncode}"
        print(f"Policy: {policy.source}")
        print(f"Sandbox: {status} in {result.duration_ms} ms")
        print(f"Working directory: {result.working_directory}")
        if result.stdout:
            print("--- stdout ---")
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print("--- stderr ---")
            print(result.stderr, end="" if result.stderr.endswith("\n") else "\n")
        if result.stdout_truncated:
            print("[stdout truncated]")
        if result.stderr_truncated:
            print("[stderr truncated]")

    if result.timed_out:
        return 124
    if result.returncode is None:
        return 1
    if 0 <= result.returncode <= 255:
        return result.returncode
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen-capabilities",
        description="Audit or use named policies for the existing Lumen sandbox.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser(
        "list",
        help="Validate and list capability manifests without executing anything.",
    )
    list_parser.add_argument("--file", default="")
    list_parser.set_defaults(func=cmd_list)

    run_parser = subparsers.add_parser(
        "run",
        help="Run a sandbox command using a named manifest or manual allowlist.",
    )
    run_parser.add_argument("--file", default="")
    run_parser.add_argument("--manifest", default="")
    run_parser.add_argument("--allow", action="append", default=[], metavar="NAME")
    run_parser.add_argument("--timeout", type=float, default=None)
    run_parser.add_argument("--max-output-bytes", type=int, default=None)
    run_parser.add_argument("--json", action="store_true")
    run_parser.add_argument("argv", nargs=argparse.REMAINDER)
    run_parser.set_defaults(func=cmd_run)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
