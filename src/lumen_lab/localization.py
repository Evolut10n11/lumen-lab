from __future__ import annotations

from typing import Any

SUPPORTED_LOCALES = {"en", "ru"}
DEFAULT_LOCALE = "en"


def normalize_locale(value: object, *, default: str = DEFAULT_LOCALE) -> str:
    """Return a supported product locale from a user/client supplied value."""
    if isinstance(value, str):
        candidate = value.strip().casefold().replace("_", "-").split("-", 1)[0]
        if candidate in SUPPORTED_LOCALES:
            return candidate
    return default


def locale_from_context(context: dict[str, Any] | None, *, default: str = DEFAULT_LOCALE) -> str:
    if not isinstance(context, dict):
        return default
    return normalize_locale(context.get("locale"), default=default)


def is_russian(locale: object) -> bool:
    return normalize_locale(locale) == "ru"
