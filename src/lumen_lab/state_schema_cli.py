from __future__ import annotations

import argparse
import json
from pathlib import Path

from .state_schema import (
    MANIFEST_NAME,
    migrate_legacy_manifest,
    migration_plan,
    validate_state_schema,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lumen-schema",
        description="Inspect and safely migrate Lumen state schema metadata.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current directory).",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--migrate",
        action="store_true",
        help=f"Create state/{MANIFEST_NAME} for a validated legacy repository.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        before = migration_plan(args.root)
        if args.migrate:
            migrate_legacy_manifest(args.root)
        manifest_path = args.root / "state" / MANIFEST_NAME
        manifest = validate_state_schema(args.root) if manifest_path.exists() else None
        after = migration_plan(args.root)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"state schema error: {exc}")
        return 2

    payload = {
        "before": before,
        "after": after,
        "migrated": bool(args.migrate and before["status"] == "legacy-unversioned"),
        "manifest": manifest.to_dict() if manifest is not None else None,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print("Lumen State Schema")
    print(f"Status: {after['status']}")
    if payload["migrated"]:
        print(f"Migration: created state/{MANIFEST_NAME}; existing payload files were unchanged")
    elif before["changes"]:
        print("Plan:")
        for change in before["changes"]:
            print(f"  - {change}")
        print("Apply with: lumen-schema --migrate")
    else:
        print("Plan: no migration required")
    if manifest is not None:
        print(f"Manifest version: {manifest.manifest_version}")
        print(f"Managed files: {len(manifest.files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
