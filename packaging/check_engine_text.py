"""Black-box text contract for the actual standalone/installed desktop engine.

Run with --engine path/to/lumen-engine.exe. No Lumen imports and no mocked stdio:
the driver sends precisely the UTF-8 bytes that the Tauri host sends.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

NAME = "Иван Ёж 🧑‍💻"
CONTEXT = "Учусь и делаю проект. 東京 café 🚀"
CHANGE = "Хочу завершить макет 🚀"
GOAL = "Завершить макет 🚀"
FRICTION = "Мало времени — только полчаса"


def call_engine(
    command: list[str], root: Path, action: str, locale: str = "ru",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = {
        "action": action, "user_id": "text-contract", "locale": locale,
        "payload": {} if payload is None else payload,
    }
    # Contradictory settings must not change the wire contract, including when
    # the embedded PyInstaller interpreter ignores these environment variables.
    env = os.environ.copy()
    env.update(PYTHONUTF8="0", PYTHONIOENCODING="cp1251", PYTHONLEGACYWINDOWSSTDIO="1")
    result = subprocess.run(
        command, input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        capture_output=True, cwd=root, env=env, timeout=60, check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Engine failed: action={action}, exit={result.returncode}, "
            f"stderr={result.stderr.decode('utf-8', errors='backslashreplace')!r}, "
            f"stdout={result.stdout!r}"
        )
    raw = result.stdout.decode("utf-8", errors="strict")
    response = json.loads(raw)
    assert response["ok"] is True, response
    decoded = json.dumps(response, ensure_ascii=False)
    assert "\ufffd" not in decoded, "Replacement characters reached the UI payload"
    assert not any(0xD800 <= ord(char) <= 0xDFFF for char in decoded)
    return response["data"]


def check_dashboard(data: dict[str, Any], locale: str) -> None:
    assert data["user"]["display_name"] == NAME, data["user"]
    assert GOAL in data["user"]["priorities"], data["user"]["priorities"]
    assert data["context"]["answers"]["current_context"] == CONTEXT
    assert data["context"]["answers"]["desired_change"] == CHANGE
    assert data["context"]["answers"]["friction"] == FRICTION
    assert data["today"]["focus_minutes"] == 30
    if locale == "ru":
        assert data["experience"]["headline"] == f"Одно полезное действие, {NAME}."
        assert data["experience"]["primary_action"]["label"] in {"Начать", "Продолжить"}
        assert [item["label"] for item in data["experience"]["quick_actions"]] == [
            "Больше такого", "Не сейчас", "Меньше такого",
        ]
        assert data["today"]["title"] == f"Продвинуться в цели: {GOAL}"
        assert data["today"]["steps"][0]["text"].startswith("Переформулируйте цель")
    else:
        assert data["experience"]["headline"] == f"One useful thing, {NAME}."


def exercise(command: list[str], root: Path) -> None:
    root.mkdir(parents=True)
    first = call_engine(command, root, "bootstrap")
    assert first["initialized"] is False
    data = call_engine(command, root, "guided_onboard", payload={
        "display_name": NAME, "current_context": CONTEXT, "desired_change": CHANGE,
        "friction": FRICTION, "focus_minutes": 30,
    })
    check_dashboard(data, "ru")
    mission_id = data["today"]["mission_id"]
    call_engine(command, root, "complete_step", payload={"mission_id": mission_id, "step": 1})
    # Each call is a new process; this checks persistence, not an in-memory echo.
    for locale in ("ru", "en", "ru"):
        restarted = call_engine(command, root, "bootstrap", locale)
        assert restarted["initialized"] is True
        dashboard = restarted["dashboard"]
        check_dashboard(dashboard, locale)
        assert dashboard["today"]["mission_id"] == mission_id
        assert dashboard["today"]["progress"]["completed"] == 1
    workspace = root / ".lumen" / "users" / "text-contract"
    profile = json.loads((workspace / "profile.json").read_text(encoding="utf-8"))
    assert profile["display_name"] == NAME
    assert GOAL in profile["priorities"]
    for path in workspace.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "\ufffd" not in json.dumps(data, ensure_ascii=False)
    print("PASS: Unicode names/UI, emoji, saved answers, restart, locale switch and progress")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=Path, required=True)
    args = parser.parse_args()
    engine = args.engine.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="lumen-text-contract-") as temporary:
        exercise([str(engine)], Path(temporary) / "Данные приложения")


if __name__ == "__main__":
    main()
