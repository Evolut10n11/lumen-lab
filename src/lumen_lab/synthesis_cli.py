import argparse
from pathlib import Path

from .store import LabStore
from .synthesis import render_synthesis


def run(write: bool = False) -> int:
    store = LabStore(Path.cwd())
    journal_before = store.journal_path.read_text(encoding="utf-8") if store.journal_path.exists() else ""
    content = render_synthesis(store.load(), store.load_outcomes(), journal_before)
    if write:
        store.state_dir.mkdir(parents=True, exist_ok=True)
        destination = store.state_dir / "SYNTHESIS.md"
        destination.write_text(content, encoding="utf-8")
        print("Synthesis written to state/SYNTHESIS.md")
    else:
        print(content, end="")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="lumen-synthesize",
        description="Preview or write a deterministic synthesis of Lumen Lab evidence.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write state/SYNTHESIS.md. Without this flag, print a preview only.",
    )
    args = parser.parse_args()
    return run(write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
