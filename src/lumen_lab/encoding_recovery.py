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
_MAX_DECODING_DEPTH = 3
_QUOTE_PAIRS = (("«", "»"), ("“", "”"), ('"', '"'), ("'", "'"))
_WORKSPACE_SCAN_CACHE: dict[Path, tuple[tuple[str, int, int, int], ...]] = {}
_WORKSPACE_SCAN_CACHE_LOCK = threading.Lock()


def _mojibake_score(value: str) -> int:
    return sum(value.count(marker) for marker in _MOJIBAKE_MARKERS)


def _is_single_cyrillic_unit(value: str, candidate: str, encoding: str) -> bool:
    cyrillic = [character for character in candidate if 0x0400 <= ord(character) <= 0x04FF]
    if len(cyrillic) != 1 or encoding != "cp1251":
        return False
    safe_source = all(
        unicodedata.name(character, "").startswith("CYRILLIC")
        for character in value
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


def _repair_strong_runs(value: str) -> str:
    """Repair every run containing at least two adjacent encoded UTF-8 units."""

    output: list[str] = []
    index = 0
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
            candidate = _repair_whole_text(content, allow_single_units=True)
            return f"{match.group(1)}{candidate}{match.group(3)}"

        repaired = pattern.sub(replace, repaired)
    return repaired


def _repair_token_fragment(value: str, *, allow_single_units: bool) -> str:
    repaired = _repair_whole_text(value, allow_single_units=allow_single_units)
    if repaired != value:
        return repaired
    if allow_single_units:
        repaired = _repair_quoted_units(value)
    return _repair_strong_runs(repaired)


def repair_mojibake_text(value: str, *, allow_single_units: bool = False) -> str:
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
) -> bool | None:
    try:
        source_bytes = path.read_bytes()
        original = json.loads(source_bytes.decode("utf-8"))
        repaired = repair_mojibake_json(
            original,
            allow_single_units=allow_single_units,
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

            incomplete_v021_paths: set[Path] = set()
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
                    expected_v021_state = repair_mojibake_json(
                        backup_payload,
                        allow_single_units=False,
                    )
                    if live_payload == expected_v021_state:
                        incomplete_v021_paths.add(path)

            repaired: list[Path] = []
            failed = False
            for path in paths:
                result = _repair_json_file_locked(
                    path,
                    allow_single_units=(
                        live_strong_evidence or path in incomplete_v021_paths
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
