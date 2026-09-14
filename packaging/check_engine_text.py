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
from statistics import median
from time import perf_counter
from typing import Any

NAME = "Иван Ёж 🧑‍💻"
CONTEXT = "Учусь и делаю проект. 東京 café 🚀"
CHANGE = "Хочу завершить макет 🚀"
GOAL = "Завершить макет 🚀"
FRICTION = "Мало времени — только полчаса"


def positive_milliseconds(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("timing budgets must be greater than zero")
    return parsed


def summarize_timings(timings: list[tuple[str, float]]) -> tuple[float, float]:
    samples = [elapsed for _, elapsed in timings]
    if not samples:
        raise ValueError("at least one timing sample is required")
    return median(samples), max(samples)


def assert_timing_budget(
    timings: list[tuple[str, float]],
    max_median_ms: float | None = None,
    max_sample_ms: float | None = None,
) -> tuple[float, float]:
    median_ms, max_ms = summarize_timings(timings)
    if max_median_ms is not None and median_ms > max_median_ms:
        raise AssertionError(
            "Fresh engine process median exceeded the CI budget: "
            f"{median_ms:.0f} ms > {max_median_ms:.0f} ms"
        )
    if max_sample_ms is not None and max_ms > max_sample_ms:
        raise AssertionError(
            "Fresh engine process sample exceeded the CI budget: "
            f"{max_ms:.0f} ms > {max_sample_ms:.0f} ms"
        )
    return median_ms, max_ms


def call_engine(
    command: list[str], root: Path, action: str, locale: str = "ru",
    payload: dict[str, Any] | None = None,
    timings: list[tuple[str, float]] | None = None,
) -> dict[str, Any]:
    request = {
        "action": action, "user_id": "text-contract", "locale": locale,
        "payload": {} if payload is None else payload,
    }
    # Contradictory settings must not change the wire contract, including when
    # the embedded PyInstaller interpreter ignores these environment variables.
    env = os.environ.copy()
    env.update(PYTHONUTF8="0", PYTHONIOENCODING="cp1251", PYTHONLEGACYWINDOWSSTDIO="1")
    started = perf_counter()
    result = subprocess.run(
        command, input=json.dumps(request, ensure_ascii=False).encode("utf-8"),
        capture_output=True, cwd=root, env=env, timeout=60, check=False,
    )
    elapsed_ms = (perf_counter() - started) * 1000
    if timings is not None:
        timings.append((action, elapsed_ms))
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


def exercise(
    command: list[str],
    root: Path,
    max_median_ms: float | None = None,
    max_sample_ms: float | None = None,
) -> None:
    root.mkdir(parents=True)
    timings: list[tuple[str, float]] = []
    first = call_engine(command, root, "bootstrap", timings=timings)
    assert first["initialized"] is False
    data = call_engine(command, root, "guided_onboard", payload={
        "display_name": NAME, "current_context": CONTEXT, "desired_change": CHANGE,
        "friction": FRICTION, "focus_minutes": 30,
    }, timings=timings)
    check_dashboard(data, "ru")
    mission_id = data["today"]["mission_id"]
    call_engine(
        command,
        root,
        "complete_step",
        payload={"mission_id": mission_id, "step": 1},
        timings=timings,
    )
    # Each call is a new process; this checks persistence, not an in-memory echo.
    for locale in ("ru", "en", "ru"):
        restarted = call_engine(command, root, "bootstrap", locale, timings=timings)
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
    median_ms, max_ms = assert_timing_budget(timings, max_median_ms, max_sample_ms)
    print(
        "TIMING: fresh engine process "
        f"median={median_ms:.0f} ms max={max_ms:.0f} ms samples={len(timings)}"
    )
    print("PASS: Unicode names/UI, emoji, saved answers, restart, locale switch and progress")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument(
        "--max-median-ms",
        type=positive_milliseconds,
        help="Optional maximum median fresh-process latency in milliseconds.",
    )
    parser.add_argument(
        "--max-sample-ms",
        type=positive_milliseconds,
        help="Optional maximum single fresh-process latency in milliseconds.",
    )
    args = parser.parse_args()
    engine = args.engine.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="lumen-text-contract-") as temporary:
        exercise(
            [str(engine)],
            Path(temporary) / "Данные приложения",
            max_median_ms=args.max_median_ms,
            max_sample_ms=args.max_sample_ms,
        )


if __name__ == "__main__":
    main()
