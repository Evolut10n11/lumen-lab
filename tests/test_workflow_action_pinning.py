from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS = Path(".github/workflows")
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)", re.MULTILINE)
COMMIT_REF_RE = re.compile(r"^[0-9a-f]{40}$")
CHECKOUT_ACTION = "uses: actions/checkout@"
NON_PUSH_CHECKOUT_COUNTS = {
    "branch-hygiene.yml": 1,
    "ci.yml": 1,
    "desktop-ci.yml": 2,
    "windows-installer.yml": 2,
}


def _checkout_persists_credentials_disabled(lines: list[str], index: int) -> bool:
    uses_indent = len(lines[index]) - len(lines[index].lstrip())

    for line in lines[index + 1 :]:
        stripped = line.lstrip()
        if not stripped:
            continue
        indent = len(line) - len(stripped)
        if stripped.startswith("- ") and indent <= uses_indent:
            break
        if stripped == "persist-credentials: false":
            return True
    return False


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


def test_non_push_checkouts_do_not_persist_workflow_credentials() -> None:
    violations: list[str] = []

    for filename, expected_count in NON_PUSH_CHECKOUT_COUNTS.items():
        workflow = WORKFLOWS / filename
        lines = workflow.read_text(encoding="utf-8").splitlines()
        checkout_indexes = [
            index for index, line in enumerate(lines) if CHECKOUT_ACTION in line
        ]
        if len(checkout_indexes) != expected_count:
            violations.append(
                f"{workflow}: expected {expected_count} checkout step(s), "
                f"found {len(checkout_indexes)}"
            )
            continue
        for index in checkout_indexes:
            if not _checkout_persists_credentials_disabled(lines, index):
                violations.append(
                    f"{workflow}:{index + 1}: checkout must set "
                    "persist-credentials: false"
                )

    assert violations == [], "\n".join(violations)


def test_pulse_checkout_is_the_explicit_git_push_exception() -> None:
    workflow = WORKFLOWS / "pulse.yml"
    lines = workflow.read_text(encoding="utf-8").splitlines()
    checkout_indexes = [
        index for index, line in enumerate(lines) if CHECKOUT_ACTION in line
    ]

    assert len(checkout_indexes) == 1
    assert not _checkout_persists_credentials_disabled(lines, checkout_indexes[0])
    assert any(line.strip() == "git push" for line in lines)
