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


def _is_single_cyrillic_unit(value: str, candidate: str, encoding: str) -> bool:
    cyrillic = [character for character in candidate if 0x0400 <= ord(character) <= 0x04FF]
    if len(cyrillic) != 1:
        return False
    if encoding == "cp1251":
        return value.startswith(("Р", "С"))
    return value.startswith(("Ð", "Ñ"))


def _repair_whole_text(value: str, *, allow_single_units: bool) -> str:
    before_score = _mojibake_score(value)
    if before_score < (1 if allow_single_units else 2):
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
            allow_single_units
            and marker_reduction == 1
            and len(candidate) < len(value)
            and _is_single_cyrillic_unit(value, candidate, encoding)
            and candidate.encode("utf-8").decode(encoding) == value
        )
        if candidate != value and (marker_reduction >= 2 or strong_single_unit):
            if candidate_score < best_score:
                best = candidate
                best_score = candidate_score
    return best


def _repair_token_fragment(value: str, *, allow_single_units: bool) -> str:
    repaired = _repair_whole_text(value, allow_single_units=allow_single_units)
    if repaired != value:
        return repaired

    for start, character in enumerate(value):
        if character not in _MOJIBAKE_MARKERS:
            continue
        for end in range(len(value), start + 1, -1):
            fragment = value[start:end]
            repaired_fragment = _repair_whole_text(
                fragment,
                allow_single_units=allow_single_units,
            )
            if repaired_fragment != fragment:
                # Earliest marker and longest valid span preserve surrounding
                # localized punctuation without exploring every shorter match.
                return f"{value[:start]}{repaired_fragment}{value[end:]}"
    return value


def repair_mojibake_text(value: str, *, allow_single_units: bool = False) -> str:
    """Reverse high-confidence mojibake in complete or localized mixed strings.

    Older Windows desktop builds could decode user-entered UTF-8 with the active
    code page before inserting that text into valid localized templates. The
    round trip is lossless, and the marker guard prevents ordinary Russian or
    Western text from being rewritten. Multiple passes cover repeated decoding.
    """

    repaired = value
    evidence_found = allow_single_units
    for _ in range(_MAX_REPAIR_PASSES):
        whole = _repair_whole_text(repaired, allow_single_units=evidence_found)
        if whole != repaired:
            repaired = whole
            evidence_found = True
            continue
        parts = re.split(r"(\s+)", repaired)
        segmented = "".join(
            part
            if part.isspace()
            else _repair_token_fragment(part, allow_single_units=evidence_found)
            for part in parts
        )
        if segmented == repaired:
            break
        repaired = segmented
        evidence_found = True
    return repaired


def _has_strong_mojibake(value: Any) -> bool:
    if isinstance(value, str):
        return repair_mojibake_text(value) != value
    if isinstance(value, list):
        return any(_has_strong_mojibake(item) for item in value)
    if isinstance(value, dict):
        return any(
            (isinstance(key, str) and _has_strong_mojibake(key))
            or _has_strong_mojibake(item)
            for key, item in value.items()
        )
    return False


def repair_mojibake_json(value: Any, *, allow_single_units: bool | None = None) -> Any:
    """Repair strings and string keys recursively in JSON-compatible state."""

    if allow_single_units is None:
        allow_single_units = _has_strong_mojibake(value)
    if isinstance(value, str):
        return repair_mojibake_text(value, allow_single_units=allow_single_units)
    if isinstance(value, list):
        return [
            repair_mojibake_json(item, allow_single_units=allow_single_units)
            for item in value
        ]
    if isinstance(value, dict):
        keys = [
            repair_mojibake_text(key, allow_single_units=allow_single_units)
            if isinstance(key, str)
            else key
            for key in value
        ]
        key_counts = Counter(keys)
        repaired: dict[Any, Any] = {}
        for (key, item), repaired_key in zip(value.items(), keys, strict=True):
            # If old and new spellings coexist, retain both original keys. This
            # preserves both values regardless of their insertion order.
            if key_counts[repaired_key] > 1:
                repaired_key = key
            repaired[repaired_key] = repair_mojibake_json(
                item,
                allow_single_units=allow_single_units,
            )
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


def repair_json_file(path: Path, *, allow_single_units: bool | None = None) -> bool:
    """Repair one valid JSON file atomically and retain its original bytes once."""

    try:
        original = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False

    repaired = repair_mojibake_json(original, allow_single_units=allow_single_units)
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

    if not directory.is_dir():
        return ()
    paths = sorted(directory.glob("*.json"))
    allow_single_units = False
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if _has_strong_mojibake(payload):
            allow_single_units = True
            break

    repaired: list[Path] = []
    for path in paths:
        if repair_json_file(path, allow_single_units=allow_single_units):
            repaired.append(path)
    return tuple(repaired)
