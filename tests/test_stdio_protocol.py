from __future__ import annotations

import io
import json
import sys
from typing import Any

import pytest

from lumen_lab.stdio_protocol import serve

SAMPLE = {"name": "Иван Ёж 🧑‍💻", "goal": "Завершить макет 🚀", "mixed": "東京 café"}


def run_pipe(monkeypatch, raw: bytes, codec: str, dispatch):
    incoming = io.TextIOWrapper(io.BytesIO(raw), encoding=codec, errors="surrogateescape")
    outgoing_bytes = io.BytesIO()
    outgoing = io.TextIOWrapper(outgoing_bytes, encoding=codec, errors="strict")
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdin", incoming)
        patch.setattr(sys, "stdout", outgoing)
        code = serve(dispatch)
        outgoing.flush()
        response_bytes = outgoing_bytes.getvalue()
    return code, json.loads(response_bytes.decode("utf-8", errors="strict"))


@pytest.mark.parametrize("codec", ["cp1251", "cp1252", "cp866", "ascii", "utf-8"])
@pytest.mark.parametrize("escaped", [False, True])
def test_exact_unicode_roundtrip_under_legacy_text_streams(monkeypatch, codec, escaped):
    request = json.dumps(SAMPLE, ensure_ascii=escaped).encode("utf-8")
    code, response = run_pipe(
        monkeypatch, request, codec,
        lambda value: {"echo": value, "headline": "Одно полезное действие", "button": "Начать"},
    )
    assert code == 0
    assert response == {
        "ok": True,
        "data": {"echo": SAMPLE, "headline": "Одно полезное действие", "button": "Начать"},
    }


@pytest.mark.parametrize("raw", [b"", b"   ", b"\xff", b"{", b"[]"])
def test_invalid_wire_input_never_reaches_dispatch(monkeypatch, raw):
    calls = []
    code, response = run_pipe(monkeypatch, raw, "cp1251", lambda value: calls.append(value))
    assert code == 2
    assert response["ok"] is False
    assert isinstance(response["error"]["message"], str)
    assert not calls


def test_accepts_utf8_bom_without_codepage_guessing(monkeypatch):
    code, response = run_pipe(
        monkeypatch, b"\xef\xbb\xbf" + json.dumps(SAMPLE, ensure_ascii=False).encode("utf-8"),
        "cp1251", lambda value: value,
    )
    assert code == 0
    assert response["data"] == SAMPLE


def test_localized_errors_are_lossless(monkeypatch):
    def fail(_request: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("Не удалось прочитать профиль — повторите попытку 🛠")

    code, response = run_pipe(monkeypatch, b"{}", "cp1252", fail)
    assert code == 2
    assert response["error"]["message"] == "Не удалось прочитать профиль — повторите попытку 🛠"


def test_escaped_surrogate_is_removed_but_valid_emoji_survives(monkeypatch):
    code, response = run_pipe(
        monkeypatch, b'{"name":"A\\udc98B", "emoji":"\\ud83d\\ude80"}',
        "cp1251", lambda value: value,
    )
    assert code == 0
    assert response["data"] == {"name": "AB", "emoji": "🚀"}


def test_stringio_embedding_still_works(monkeypatch):
    output = io.StringIO()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdin", io.StringIO(json.dumps(SAMPLE, ensure_ascii=False)))
        patch.setattr(sys, "stdout", output)
        assert serve(lambda value: value) == 0
    assert json.loads(output.getvalue())["data"] == SAMPLE


def test_previous_text_pipe_path_reproduces_the_reported_symptom():
    # The old implementation decoded UTF-8 request bytes as cp1251, wrote native
    # Russian literals as cp1251, then the host decoded them with UTF-8 replacement.
    original = {"goal": "Завершить макет"}
    request = json.dumps(original, ensure_ascii=False).encode("utf-8")
    wrongly_decoded = json.loads(request.decode("cp1251"))
    assert wrongly_decoded != original
    outgoing = json.dumps(
        {"headline": "Одно полезное действие", "goal": wrongly_decoded["goal"]},
        ensure_ascii=False,
    ).encode("cp1251")
    displayed = json.loads(outgoing.decode("utf-8", errors="replace"))
    assert "\ufffd" in displayed["headline"]
    assert displayed["goal"] == original["goal"]
