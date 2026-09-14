from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS = Path(".github/workflows")
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)", re.MULTILINE)
COMMIT_REF_RE = re.compile(r"^[0-9a-f]{40}$")


def test_external_github_actions_are_pinned_to_full_commit_shas() -> None:
    unpinned: list[str] = []

    for workflow in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml"))):
        content = workflow.read_text(encoding="utf-8")
        for action in USES_RE.findall(content):
            if action.startswith(("./", "docker://")):
                continue
            if "@" not in action:
                unpinned.append(f"{workflow}: {action} (missing @ref)")
                continue
            _, ref = action.rsplit("@", 1)
            if COMMIT_REF_RE.fullmatch(ref) is None:
                unpinned.append(f"{workflow}: {action}")

    assert unpinned == [], (
        "External GitHub Actions must use immutable 40-character commit SHAs; "
        "mutable tags and branches are not allowed:\n" + "\n".join(unpinned)
    )
