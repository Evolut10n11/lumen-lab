from __future__ import annotations

from pathlib import Path

import pytest

from lumen_lab.desktop_bridge import dispatch
from lumen_lab.localization import normalize_locale


def _request(
    action: str,
    *,
    user_id: str = "default",
    locale: str | None = None,
    **payload: object,
):
    request: dict[str, object] = {
        "action": action,
        "user_id": user_id,
        "payload": payload,
    }
    if locale is not None:
        request["locale"] = locale
    return dispatch(request)


def test_locale_normalization_supports_russian_language_tags() -> None:
    assert normalize_locale("ru-RU") == "ru"
    assert normalize_locale("en_US") == "en"
    assert normalize_locale("unknown") == "en"


def test_russian_guided_onboarding_localizes_product_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    bootstrap = _request("bootstrap", locale="ru")
    assert bootstrap["locale"] == "ru"
    assert bootstrap["onboarding"]["headline"] == "Что вы хотите продвинуть?"

    dashboard = _request(
        "guided_onboard",
        locale="ru",
        display_name="Иван",
        current_context="Работаю и пытаюсь запустить свой проект",
        desired_change="Хочу лучше заботиться о себе",
        friction="Слишком много параллельных дел",
        focus_minutes=30,
    )

    assert dashboard["locale"] == "ru"
    assert dashboard["context"]["locale"] == "ru"
    assert dashboard["experience"]["headline"].startswith("Одно полезное действие")
    assert dashboard["today"]["title"].startswith("Продвинуться в цели")
    assert "Вы обозначили" in dashboard["today"]["why_now"]
    assert dashboard["today"]["steps"][0]["text"].startswith("Переформулируйте")
    assert dashboard["context"]["hypotheses"][0]["label"] == "Что вы хотите изменить"

    persisted = _request("bootstrap")
    assert persisted["locale"] == "ru"
    assert persisted["dashboard"]["locale"] == "ru"
