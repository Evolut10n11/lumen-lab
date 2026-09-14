from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import unicodedata
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from .state_io import (
    fsync_parent_directory,
    json_path_lock,
    write_json_atomic_unlocked,
)

_LEGACY_ENCODINGS = ("cp1251", "cp1252", "latin1")
_MOJIBAKE_MARKERS = ("Р", "С", "Ð", "Ñ", "Ã", "Â", "â")
_RUSSIAN_ALPHABET = frozenset(
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
)
_MAX_DECODING_DEPTH = 3
_QUOTE_PAIRS = (("«", "»"), ("“", "”"), ('"', '"'), ("'", "'"))
_WORKSPACE_SCAN_CACHE: dict[Path, tuple[tuple[str, int, int, int], ...]] = {}
_WORKSPACE_SCAN_CACHE_LOCK = threading.Lock()
_NO_REPLACEMENT = object()
_V021_UNPROVEN = object()
_V021_WORK_BUDGET = 250_000


class _V021BudgetExhausted(Exception):
    pass


def _mojibake_score(value: str) -> int:
    return sum(value.count(marker) for marker in _MOJIBAKE_MARKERS)


def _is_single_cyrillic_unit(value: str, candidate: str, encoding: str) -> bool:
    cyrillic = [character for character in candidate if 0x0400 <= ord(character) <= 0x04FF]
    if len(cyrillic) != 1 or encoding != "cp1251":
        return False
    source_is_cyrillic = all(
        unicodedata.name(character, "").startswith("CYRILLIC")
        for character in value
    )
    # A pair made only of Russian letters can itself be legitimate user text:
    # `Рё` is both a real name spelling and mojibake for `и`. Fail closed for
    # such ambiguous pairs, while allowing unambiguous `РЇ` -> `Я` and
    # `РЎ` -> `С`-style units whose second character is outside the alphabet.
    safe_source = source_is_cyrillic and any(
        character not in _RUSSIAN_ALPHABET for character in value
    )
    # The UTF-8 continuation byte for Cyrillic `Р` maps to NBSP in cp1251.
    safe_source = safe_source or (
        value == "Р\u00a0" and candidate == "Р"
    )
    if not safe_source:
        return False
    return value.startswith(("Р", "С"))


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
            and _is_single_cyrillic_unit(value, candidate, encoding)
            and candidate.encode("utf-8").decode(encoding) == value
        )
        if _is_fully_ambiguous_cp1251_repair(value, candidate, encoding):
            continue
        if (
            candidate != value
            and len(candidate) < len(value)
            and (marker_reduction >= 2 or strong_single_unit)
            and (candidate_score, len(candidate)) < (best_score, len(best))
        ):
            best = candidate
            best_score = candidate_score
    return best


def _decode_unit(value: str, start: int, encoding: str) -> tuple[int, str] | None:
    """Decode one reversible UTF-8 unit from a legacy-decoded string."""

    for width in range(2, min(4, len(value) - start) + 1):
        fragment = value[start : start + width]
        try:
            candidate = fragment.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if len(candidate) != 1:
            continue
        try:
            if candidate.encode("utf-8").decode(encoding) == fragment:
                return start + width, candidate
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return None


def _is_fully_ambiguous_cp1251_repair(
    value: str,
    candidate: str,
    encoding: str,
) -> bool:
    """Detect reversible cp1251 spans that are also valid Russian text.

    Some legacy-decoded UTF-8 units, such as `Рё`, are composed entirely of
    ordinary Russian letters and can therefore be legitimate user content.
    Multiple such units must not become stronger evidence merely by repetition.
    If every reversible unit in a candidate has that ambiguity, fail closed.
    """

    if encoding != "cp1251":
        return False

    rebuilt: list[str] = []
    ambiguous_units = 0
    unambiguous_units = 0
    index = 0
    while index < len(value):
        unit = _decode_unit(value, index, encoding)
        if unit is None:
            rebuilt.append(value[index])
            index += 1
            continue
        end, character = unit
        fragment = value[index:end]
        is_ambiguous = (
            0x0400 <= ord(character) <= 0x04FF
            and fragment != "Р\u00a0"
            and all(source in _RUSSIAN_ALPHABET for source in fragment)
        )
        if is_ambiguous:
            ambiguous_units += 1
        else:
            unambiguous_units += 1
        rebuilt.append(character)
        index = end

    return (
        ambiguous_units > 0
        and unambiguous_units == 0
        and "".join(rebuilt) == candidate
    )


def _repair_strong_runs(value: str, *, max_repairs: int | None = None) -> str:
    """Repair every run containing at least two adjacent encoded UTF-8 units."""

    output: list[str] = []
    index = 0
    repairs = 0
    while index < len(value):
        best: tuple[int, str] | None = None
        rejected_until = index + 1
        if value[index] in _MOJIBAKE_MARKERS:
            for encoding in _LEGACY_ENCODINGS:
                cursor = index
                decoded: list[str] = []
                while unit := _decode_unit(value, cursor, encoding):
                    cursor, character = unit
                    decoded.append(character)
                if len(decoded) < 2:
                    continue
                candidate = "".join(decoded)
                fragment = value[index:cursor]
                if _is_fully_ambiguous_cp1251_repair(
                    fragment,
                    candidate,
                    encoding,
                ):
                    rejected_until = max(rejected_until, cursor)
                    continue
                if _mojibake_score(fragment) - _mojibake_score(candidate) < 2:
                    # Every unit starts with a marker and decodes to one
                    # character, so marker reduction cannot be negative. If a
                    # maximal run has insufficient evidence, none of its
                    # suffixes can qualify; skip them instead of rescanning.
                    rejected_until = max(rejected_until, cursor)
                    continue
                if best is None or cursor > best[0]:
                    best = (cursor, candidate)
        if best is None:
            output.append(value[index:rejected_until])
            index = rejected_until
        else:
            index, candidate = best
            output.append(candidate)
            repairs += 1
            if max_repairs is not None and repairs >= max_repairs:
                output.append(value[index:])
                break
    return "".join(output)


def _repair_quoted_units(value: str) -> str:
    """Repair weak units only when the complete contents of a quote pair match."""

    repaired = value
    for opening, closing in _QUOTE_PAIRS:
        excluded = re.escape(opening + closing)
        pattern = re.compile(
            f"({re.escape(opening)})([^{excluded}]+)({re.escape(closing)})"
        )

        def replace(match: re.Match[str]) -> str:
            content = match.group(2)
            parts = re.split(r"([ \t\r\n]+)", content)
            candidate = "".join(
                part
                if part.isspace()
                else _repair_token_fragment(part, allow_single_units=True)
                for part in parts
            )
            return f"{match.group(1)}{candidate}{match.group(3)}"

        repaired = pattern.sub(replace, repaired)
    return repaired


def _repair_boundary_punctuation(value: str) -> str:
    """Repair one evidence-gated unit while preserving boundary punctuation."""

    start = 0
    end = len(value)
    while start < end and unicodedata.category(value[start]).startswith("P"):
        start += 1
    while end > start and unicodedata.category(value[end - 1]).startswith("P"):
        end -= 1
    if start == 0 and end == len(value):
        return value
    core = value[start:end]
    repaired_core = _repair_whole_text(core, allow_single_units=True)
    if repaired_core == core:
        return value
    return f"{value[:start]}{repaired_core}{value[end:]}"


def _repair_token_fragment(value: str, *, allow_single_units: bool) -> str:
    repaired = _repair_whole_text(value, allow_single_units=allow_single_units)
    if repaired != value:
        return repaired
    if allow_single_units:
        repaired = _repair_boundary_punctuation(value)
        if repaired != value:
            return repaired
        repaired = _repair_quoted_units(value)
    return _repair_strong_runs(repaired)


def repair_mojibake_text(
    value: str,
    *,
    allow_single_units: bool = False,
) -> str:
    """Reverse high-confidence mojibake in complete or localized mixed strings.

    Older Windows desktop builds could decode user-entered UTF-8 with the active
    code page before inserting that text into valid localized templates. Each
    pass repairs every independent fragment; the fixed depth covers repeated
    legacy decoding without making work depend on the number of fragments.
    """

    repaired = value
    evidence_found = allow_single_units
    for _ in range(_MAX_DECODING_DEPTH):
        whole = _repair_whole_text(repaired, allow_single_units=evidence_found)
        if whole != repaired:
            repaired = whole
            evidence_found = True
            continue
        if evidence_found:
            repaired = _repair_quoted_units(repaired)
        # Split only protocol whitespace. A cp1251 decoding of the UTF-8 bytes
        # for Cyrillic `Р` contains U+00A0, which must stay inside its fragment.
        parts = re.split(r"([ \t\r\n]+)", repaired)
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


def repair_mojibake_json(
    value: Any,
    *,
    allow_single_units: bool | None = None,
) -> Any:
    """Repair strings and string keys recursively in JSON-compatible state."""

    if allow_single_units is None:
        allow_single_units = _has_strong_mojibake(value)
    if isinstance(value, str):
        return repair_mojibake_text(
            value,
            allow_single_units=allow_single_units,
        )
    if isinstance(value, list):
        return [
            repair_mojibake_json(
                item,
                allow_single_units=allow_single_units,
            )
            for item in value
        ]
    if isinstance(value, dict):
        keys = [
            repair_mojibake_text(
                key,
                allow_single_units=allow_single_units,
            )
            if isinstance(key, str)
            else key
            for key in value
        ]
        key_counts = Counter(keys)
        original_keys = set(value)
        repaired: dict[Any, Any] = {}
        for (key, item), repaired_key in zip(value.items(), keys, strict=True):
            # Preserve original spellings whenever a destination is ambiguous
            # or already names another source key. No value may be overwritten.
            if key_counts[repaired_key] > 1 or (
                repaired_key != key and repaired_key in original_keys
            ):
                repaired_key = key
            if repaired_key in repaired and repaired_key != key:
                repaired_key = key
            repaired[repaired_key] = repair_mojibake_json(
                item,
                allow_single_units=allow_single_units,
            )
        return repaired
    return value


def _spend_v021_budget(budget: list[int], value: str) -> None:
    budget[0] -= max(1, len(value))
    if budget[0] < 0:
        raise _V021BudgetExhausted


def _repair_v021_whole_text(value: str, budget: list[int]) -> str:
    """Reproduce the strict whole-value rule shipped in Lumen 0.2.1."""

    _spend_v021_budget(budget, value)
    before_score = _mojibake_score(value)
    if before_score < 2:
        return value
    best = value
    best_score = before_score
    for encoding in _LEGACY_ENCODINGS:
        try:
            candidate = value.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        candidate_score = _mojibake_score(candidate)
        if candidate != value and candidate_score <= before_score - 2:
            if candidate_score < best_score:
                best = candidate
                best_score = candidate_score
    return best


def _repair_v021_token_fragment(value: str, budget: list[int]) -> str:
    repaired = _repair_v021_whole_text(value, budget)
    if repaired != value:
        return repaired
    for start, character in enumerate(value):
        if character not in _MOJIBAKE_MARKERS:
            continue
        for end in range(len(value), start + 1, -1):
            fragment = value[start:end]
            repaired_fragment = _repair_v021_whole_text(fragment, budget)
            if repaired_fragment != fragment:
                return f"{value[:start]}{repaired_fragment}{value[end:]}"
    return value


def _repair_v021_text(value: str, budget: list[int]) -> str:
    """Reproduce v0.2.1's three-pass, Unicode-whitespace migration output."""

    repaired = value
    for _ in range(3):
        whole = _repair_v021_whole_text(repaired, budget)
        if whole != repaired:
            repaired = whole
            continue
        parts = re.split(r"(\s+)", repaired)
        segmented = "".join(
            part if part.isspace() else _repair_v021_token_fragment(part, budget)
            for part in parts
        )
        if segmented == repaired:
            break
        repaired = segmented
    return repaired


def _repair_v021_json_value(value: Any, budget: list[int]) -> Any:
    if isinstance(value, str):
        return _repair_v021_text(value, budget)
    if isinstance(value, list):
        return [_repair_v021_json_value(item, budget) for item in value]
    if isinstance(value, dict):
        keys = [
            _repair_v021_text(key, budget) if isinstance(key, str) else key
            for key in value
        ]
        key_counts = Counter(keys)
        repaired: dict[Any, Any] = {}
        for (key, item), repaired_key in zip(value.items(), keys, strict=True):
            if key_counts[repaired_key] > 1:
                repaired_key = key
            repaired[repaired_key] = _repair_v021_json_value(item, budget)
        return repaired
    return value


def _repair_v021_json(value: Any) -> Any:
    budget = [_V021_WORK_BUDGET]
    try:
        return _repair_v021_json_value(value, budget)
    except _V021BudgetExhausted:
        return _V021_UNPROVEN


def _json_equal_strict(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _json_equal_strict(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _json_equal_strict(left[key], right[key]) for key in left
        )
    return bool(left == right)


def _valid_json_bytes(data: bytes) -> bool:
    try:
        json.loads(data.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return False
    return True


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        fsync_parent_directory(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _backup_original(backup: Path, source_bytes: bytes) -> None:
    if backup.exists():
        backup_bytes = backup.read_bytes()
        if backup_bytes == source_bytes:
            fsync_parent_directory(backup)
            return
        if _valid_json_bytes(backup_bytes):
            digest = hashlib.sha256(source_bytes).hexdigest()[:12]
            snapshot = backup.with_name(f"{backup.name}.{digest}")
            if snapshot.exists():
                if snapshot.read_bytes() != source_bytes:
                    raise OSError("encoding recovery snapshot digest collision")
                fsync_parent_directory(snapshot)
            else:
                _write_bytes_atomic(snapshot, source_bytes)
            return
    _write_bytes_atomic(backup, source_bytes)


def _repair_json_file_locked(
    path: Path,
    *,
    allow_single_units: bool | None = None,
    replacement: Any = _NO_REPLACEMENT,
    expected_original: Any = _NO_REPLACEMENT,
) -> bool | None:
    try:
        source_bytes = path.read_bytes()
        original = json.loads(source_bytes.decode("utf-8"))
        if expected_original is not _NO_REPLACEMENT and not _json_equal_strict(
            original,
            expected_original,
        ):
            return None
        repaired = (
            repair_mojibake_json(
                original,
                allow_single_units=allow_single_units,
            )
            if replacement is _NO_REPLACEMENT
            else replacement
        )
        if repaired == original:
            return False

        backup = path.with_name(f"{path.name}.before-encoding-repair")
        _backup_original(backup, source_bytes)
        # Detect a non-cooperating write that landed before the final check.
        if path.read_bytes() != source_bytes:
            return None
        write_json_atomic_unlocked(path, repaired)
        return True
    except (OSError, UnicodeError, json.JSONDecodeError):
        # A read-only or otherwise inaccessible profile should remain loadable;
        # recovery must never turn an encoding display problem into lost state.
        return None


def repair_json_file(path: Path, *, allow_single_units: bool | None = None) -> bool:
    """Repair one valid JSON file atomically and retain exact original bytes."""

    try:
        with json_path_lock(path):
            result = _repair_json_file_locked(
                path,
                allow_single_units=allow_single_units,
            )
            return result is True
    except OSError:
        return False


def _workspace_fingerprint(
    paths: list[Path],
) -> tuple[tuple[str, int, int, int], ...]:
    fingerprint: list[tuple[str, int, int, int]] = []
    for source in paths:
        candidates = (
            source,
            source.with_name(f"{source.name}.before-encoding-repair"),
        )
        for path in candidates:
            try:
                stat = path.stat()
            except OSError:
                continue
            fingerprint.append(
                (path.name, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
            )
    return tuple(fingerprint)


def repair_workspace_json(directory: Path) -> tuple[Path, ...]:
    """Repair persisted user JSON before models validate or render it."""

    if not directory.is_dir():
        return ()
    paths = sorted(directory.glob("*.json"))
    if not paths:
        return ()
    try:
        with json_path_lock(paths[0]):
            resolved_directory = directory.resolve()
            fingerprint = _workspace_fingerprint(paths)
            with _WORKSPACE_SCAN_CACHE_LOCK:
                if _WORKSPACE_SCAN_CACHE.get(resolved_directory) == fingerprint:
                    return ()

            live_payloads: dict[Path, Any] = {}
            live_strong_evidence = False
            for path in paths:
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    continue
                live_payloads[path] = payload
                live_strong_evidence = live_strong_evidence or _has_strong_mojibake(
                    payload
                )

            v021_replacements: dict[Path, tuple[Any, Any]] = {}
            if not live_strong_evidence:
                for path, live_payload in live_payloads.items():
                    backup = path.with_name(
                        f"{path.name}.before-encoding-repair"
                    )
                    try:
                        backup_payload = json.loads(backup.read_text(encoding="utf-8"))
                    except (OSError, UnicodeError, json.JSONDecodeError):
                        continue
                    if not _has_strong_mojibake(backup_payload):
                        continue
                    expected_v021_state = _repair_v021_json(backup_payload)
                    if expected_v021_state is _V021_UNPROVEN:
                        continue
                    if _json_equal_strict(live_payload, expected_v021_state):
                        v021_replacements[path] = (
                            live_payload,
                            repair_mojibake_json(
                                backup_payload,
                                allow_single_units=True,
                            ),
                        )

            repaired: list[Path] = []
            failed = False
            for path in paths:
                v021_proof = v021_replacements.get(path)
                result = _repair_json_file_locked(
                    path,
                    allow_single_units=(
                        live_strong_evidence or path in v021_replacements
                    ),
                    replacement=(
                        v021_proof[1]
                        if v021_proof is not None
                        else _NO_REPLACEMENT
                    ),
                    expected_original=(
                        v021_proof[0]
                        if v021_proof is not None
                        else _NO_REPLACEMENT
                    ),
                )
                if result is True:
                    repaired.append(path)
                elif result is None:
                    failed = True
            if not failed:
                with _WORKSPACE_SCAN_CACHE_LOCK:
                    _WORKSPACE_SCAN_CACHE[resolved_directory] = _workspace_fingerprint(
                        paths
                    )
            return tuple(repaired)
    except OSError:
        return ()