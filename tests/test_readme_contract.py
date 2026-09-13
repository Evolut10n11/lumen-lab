from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PYPROJECT = ROOT / "pyproject.toml"


def test_readme_mentions_every_installed_console_script() -> None:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    scripts = sorted(project["project"]["scripts"])
    readme = README.read_text(encoding="utf-8")

    missing = [script for script in scripts if f"`{script}`" not in readme]

    assert missing == [], f"README is missing installed console scripts: {missing}"


def test_readme_documentation_links_resolve_inside_repository() -> None:
    readme = README.read_text(encoding="utf-8")
    linked_docs = sorted(set(re.findall(r"\((docs/[^)#]+\.md)\)", readme)))

    assert linked_docs, "README should link to deeper documentation"
    missing = [path for path in linked_docs if not (ROOT / path).is_file()]

    assert missing == [], f"README links to missing documentation files: {missing}"
