from __future__ import annotations

import argparse
from pathlib import Path

from .doctor import run_doctor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen-doctor",
        description="Check Lumen repository state integrity without modifying files.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root containing the state directory (default: current directory).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_doctor(args.root)
    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status:<4} {check.name}: {check.detail}")
    return 0 if report.healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
