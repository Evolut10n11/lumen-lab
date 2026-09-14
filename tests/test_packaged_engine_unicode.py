from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from lumen_lab.packaged_engine import main
from lumen_lab.unicode_safety import sanitize_json_strings


def test_sanitize_json_strings_removes_lone_surrogates_recursively() -> None:
    payload = {
        "name": "Ива\udc98н",
        "nested": ["AI\ud800роль", {"goal": "Продукт\udfff"}],
    }

    sanitized = sanitize_json_strings(payload)

    assert sanitized == {
        "name": "Иван",
        "nested": ["AIроль", {"goal": "Продукт"}],
    }
    json.dumps(sanitized, ensure_ascii=False).encode("utf-8")


def test_packaged_engine_accepts_browser_json_with_lone_surrogate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    request = {
        "action": "guided_onboard",
        "user_id": "default",
        "locale": "ru",
        "payload": {
            "display_name": "Ива\udc98н",
            "current_context": "Работаю разработчиком\ud800 и готовлюсь к собеседованиям",
            "desired_change": "Хочу получить сильную AI\udfff роль",
            "friction": "Слишком много параллельных задач",
            "focus_minutes": 30,
        },
    }
    stdin = io.StringIO(json.dumps(request, ensure_ascii=True))
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)

    exit_code = main()
    raw_response = stdout.getvalue()
    response = json.loads(raw_response)

    assert exit_code == 0
    assert response["ok"] is True
    assert response["data"]["user"]["display_name"] == "Иван"
    assert "\udc98" not in raw_response
    assert "\ud800" not in raw_response
    assert "\udfff" not in raw_response
    raw_response.encode("utf-8")
