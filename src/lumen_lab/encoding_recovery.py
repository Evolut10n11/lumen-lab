from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .state_io import write_json_atomic

_LEGACY_ENCODINGS = ("cp1251", "latin1")
_MOJIBAKE_MARKERS = ("Р", "С", "Ð", "Ñ", "Ã", "Â", "â")
_MAX_REPAIR_PASSES = 3


def _mojibake_score(value: str) -> int:
    return sum(value.count(marker) for marker in _MOJIBAKE_MARKERS)


def repair_mojibake_text(value: str) -> str:
    """Reverse a high-confidence legacy-codepage decoding of UTF-8 text.

    Older Windows desktop builds could decode UTF-8 pipe bytes with the active
    code page before persisting them.  The round trip below is lossless, and the
    marker guard prevents ordinary Russian or Western text from being rewritten.
    Multiple passes cover state that was accidentally decoded more than once.
    """

    repaired = value
    for _ in range(_MAX_REPAIR_PASSES):
        before_score = _mojibake_score(repaired)
        if before_score < 2:
            break

        best = repaired
        best_score = before_score
        for encoding in _LEGACY_ENCODINGS:
            try:
                candidate = repaired.encode(encoding).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue
            candidate_score = _mojibake_score(candidate)
            if candidate != repaired and candidate_score <= before_score - 2:
                if candidate_score < best_score:
                    best = candidate
                    best_score = candidate_score

        if best == repaired:
            break
        repaired = best
    return repaired


def repair_mojibake_json(value: Any) -> Any:
    """Repair strings and string keys recursively in JSON-compatible state."""

    if isinstance(value, str):
        return repair_mojibake_text(value)
    if isinstance(value, list):
        return [repair_mojibake_json(item) for item in value]
    if isinstance(value, dict):
        repaired: dict[Any, Any] = {}
        for key, item in value.items():
            repaired_key = repair_mojibake_text(key) if isinstance(key, str) else key
            # Never lose a value if a repaired key would collide with an existing one.
            if repaired_key in repaired and repaired_key != key:
                repaired_key = key
            repaired[repaired_key] = repair_mojibake_json(item)
        return repaired
    return value


def repair_json_file(path: Path) -> bool:
    """Repair one valid JSON file atomically and retain its original bytes once."""

    try:
        original = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False

    repaired = repair_mojibake_json(original)
    if repaired == original:
        return False

    backup = path.with_name(f"{path.name}.before-encoding-repair")
    try:
        if not backup.exists():
            shutil.copy2(path, backup)
        write_json_atomic(path, repaired)
    except (OSError, UnicodeError):
        # A read-only or otherwise inaccessible profile should remain loadable;
        # recovery must never turn an encoding display problem into lost state.
        return False
    return True


def repair_workspace_json(directory: Path) -> tuple[Path, ...]:
    """Repair persisted user JSON before models validate or render it."""

    repaired: list[Path] = []
    if not directory.is_dir():
        return ()
    for path in sorted(directory.glob("*.json")):
        if repair_json_file(path):
            repaired.append(path)
    return tuple(repaired)
