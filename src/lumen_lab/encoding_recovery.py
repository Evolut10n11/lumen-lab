from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from .state_io import write_json_atomic

_LEGACY_ENCODINGS = ("cp1251", "cp1252", "latin1")
_MOJIBAKE_MARKERS = ("Р", "С", "Ð", "Ñ", "Ã", "Â", "â")
_MAX_REPAIR_PASSES = 3


def _mojibake_score(value: str) -> int:
    return sum(value.count(marker) for marker in _MOJIBAKE_MARKERS)


def _repair_whole_text(value: str) -> str:
    before_score = _mojibake_score(value)
    if before_score < 1:
        return value

    best = value
    best_score = before_score
    for encoding in _LEGACY_ENCODINGS:
        try:
            candidate = value.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        candidate_score = _mojibake_score(candidate)
        marker_reduction = before_score - candidate_score
        strong_single_unit = (
            marker_reduction == 1
            and len(candidate) < len(value)
            and any(ord(character) > 127 for character in candidate)
            and candidate.encode("utf-8").decode(encoding) == value
        )
        if candidate != value and (marker_reduction >= 2 or strong_single_unit):
            if candidate_score < best_score:
                best = candidate
                best_score = candidate_score
    return best


def _repair_token_fragment(value: str) -> str:
    repaired = _repair_whole_text(value)
    if repaired != value:
        return repaired

    for start, character in enumerate(value):
        if character not in _MOJIBAKE_MARKERS:
            continue
        for end in range(len(value), start + 1, -1):
            fragment = value[start:end]
            repaired_fragment = _repair_whole_text(fragment)
            if repaired_fragment != fragment:
                # Earliest marker and longest valid span preserve surrounding
                # localized punctuation without exploring every shorter match.
                return f"{value[:start]}{repaired_fragment}{value[end:]}"
    return value


def repair_mojibake_text(value: str) -> str:
    """Reverse high-confidence mojibake in complete or localized mixed strings.

    Older Windows desktop builds could decode user-entered UTF-8 with the active
    code page before inserting that text into valid localized templates. The
    round trip is lossless, and the marker guard prevents ordinary Russian or
    Western text from being rewritten. Multiple passes cover repeated decoding.
    """

    repaired = value
    for _ in range(_MAX_REPAIR_PASSES):
        whole = _repair_whole_text(repaired)
        if whole != repaired:
            repaired = whole
            continue
        parts = re.split(r"(\s+)", repaired)
        segmented = "".join(
            part if part.isspace() else _repair_token_fragment(part) for part in parts
        )
        if segmented == repaired:
            break
        repaired = segmented
    return repaired


def repair_mojibake_json(value: Any) -> Any:
    """Repair strings and string keys recursively in JSON-compatible state."""

    if isinstance(value, str):
        return repair_mojibake_text(value)
    if isinstance(value, list):
        return [repair_mojibake_json(item) for item in value]
    if isinstance(value, dict):
        keys = [
            repair_mojibake_text(key) if isinstance(key, str) else key
            for key in value
        ]
        key_counts = Counter(keys)
        repaired: dict[Any, Any] = {}
        for (key, item), repaired_key in zip(value.items(), keys, strict=True):
            # If old and new spellings coexist, retain both original keys. This
            # preserves both values regardless of their insertion order.
            if key_counts[repaired_key] > 1:
                repaired_key = key
            repaired[repaired_key] = repair_mojibake_json(item)
        return repaired
    return value


def _backup_original(path: Path, backup: Path) -> None:
    if backup.exists():
        return
    temporary = backup.with_name(f".{backup.name}.{uuid.uuid4().hex}.tmp")
    try:
        shutil.copy2(path, temporary)
        os.replace(temporary, backup)
    finally:
        if temporary.exists():
            temporary.unlink()


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
        _backup_original(path, backup)
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
