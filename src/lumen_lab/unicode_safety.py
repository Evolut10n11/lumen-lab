from __future__ import annotations

from typing import Any


def strip_lone_surrogates(value: str) -> str:
    """Remove UTF-16 surrogate code points that cannot be encoded as UTF-8.

    Browser strings can contain an unpaired surrogate. JSON.stringify preserves it as
    an escaped sequence, and Python's json decoder then reconstructs the surrogate as
    a code point. Removing it at the process boundary keeps user input usable instead
    of allowing hashing, UTF-8 files, or stdout to fail with UnicodeEncodeError.
    """

    return "".join(
        character
        for character in value
        if not 0xD800 <= ord(character) <= 0xDFFF
    )


def sanitize_json_strings(value: Any) -> Any:
    """Recursively make JSON-like data safe for UTF-8 persistence and transport."""

    if isinstance(value, str):
        return strip_lone_surrogates(value)
    if isinstance(value, list):
        return [sanitize_json_strings(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_json_strings(item) for item in value)
    if isinstance(value, dict):
        return {
            strip_lone_surrogates(key) if isinstance(key, str) else key: sanitize_json_strings(item)
            for key, item in value.items()
        }
    return value
