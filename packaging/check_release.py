"""Validate desktop versions and release tag provenance before publishing."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate_versions(root: Path, ref: str) -> str:
    desktop = root / "apps" / "desktop"
    versions = {
        name: json.loads((desktop / name).read_text(encoding="utf-8"))["version"]
        for name in ("package.json", "src-tauri/tauri.conf.json")
    }
    package_lock = json.loads((desktop / "package-lock.json").read_text(encoding="utf-8"))
    versions["package-lock.json"] = package_lock["version"]
    versions["package-lock.json root package"] = package_lock["packages"][""]["version"]
    versions["Cargo.toml"] = tomllib.loads(
        (desktop / "src-tauri/Cargo.toml").read_text(encoding="utf-8")
    )["package"]["version"]
    if len(set(versions.values())) != 1:
        raise ValueError(f"Desktop versions disagree: {versions}")
    version = versions["package.json"]
    if not re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?",
        version,
    ):
        raise ValueError(f"Unsupported release version: {version!r}")
    tag = f"v{version}"
    if ref.startswith("refs/tags/") and ref != f"refs/tags/{tag}":
        raise ValueError(f"Release ref {ref!r} does not match {tag!r}")
    return tag


def validate_remote_tag(output: str, tag: str, expected_sha: str) -> None:
    refs = dict(line.split()[::-1] for line in output.splitlines() if line.strip())
    name = f"refs/tags/{tag}"
    actual = refs.get(f"{name}^{{}}", refs.get(name))
    if actual is not None and actual != expected_sha:
        raise ValueError(f"Tag {tag} points to {actual}, not build commit {expected_sha}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--sha")
    args = parser.parse_args()
    tag = validate_versions(ROOT, args.ref)
    if args.sha:
        result = subprocess.run(
            ["git", "ls-remote", "--exit-code", "--tags", "origin",
             f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=60,
        )
        if result.returncode not in (0, 2):
            raise RuntimeError(f"Cannot verify remote release tag: {result.stderr.strip()}")
        validate_remote_tag(result.stdout, tag, args.sha)
    print(f"Release validation passed: {tag}")


if __name__ == "__main__":
    main()
