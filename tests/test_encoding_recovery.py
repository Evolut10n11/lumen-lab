from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lumen_lab import encoding_recovery
from lumen_lab.app_service import LumenApplication
from lumen_lab.desktop_bridge import dispatch
from lumen_lab.encoding_recovery import (
    repair_json_file,
    repair_mojibake_json,
    repair_mojibake_text,
)
from lumen_lab.onboarding import load_onboarding_context
from lumen_lab.workspace import UserWorkspace


def _legacy_decode(value: str) -> str:
    return value.encode("utf-8").decode("cp1251")


def _corrupt_strings(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return _legacy_decode(value)
        except UnicodeDecodeError:
            return value
    if isinstance(value, list):
        return [_corrupt_strings(item) for item in value]
    if isinstance(value, dict):
        return {
            _corrupt_strings(key) if isinstance(key, str) else key: _corrupt_strings(item)
            for key, item in value.items()
        }
    return value


def _corrupt_selected(value: Any, originals: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        for original in originals:
            value = value.replace(original, _legacy_decode(original))
        return value
    if isinstance(value, list):
        return [_corrupt_selected(item, originals) for item in value]
    if isinstance(value, dict):
        return {
            _corrupt_selected(key, originals) if isinstance(key, str) else key:
            _corrupt_selected(item, originals)
            for key, item in value.items()
        }
    return value


def _corrupt_selected_in_file(path: Path, originals: tuple[str, ...]) -> None:
    raw = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(
        json.dumps(_corrupt_selected(raw, originals), ensure_ascii=False),
        encoding="utf-8",
    )


def test_repair_mojibake_text_is_targeted_and_idempotent() -> None:
    broken = "РџСЂРѕРґРІРёРЅСѓС‚СЊСЃСЏ РІ С†РµР»Рё"

    assert repair_mojibake_text(broken) == "Продвинуться в цели"
    assert repair_mojibake_text("Продвинуться в цели") == "Продвинуться в цели"
    assert repair_mojibake_text(repair_mojibake_text(broken)) == "Продвинуться в цели"


def test_repair_mojibake_text_repairs_user_text_inside_russian_template() -> None:
    goal = "Завершить макет"
    broken_goal = _legacy_decode(goal)

    assert repair_mojibake_text(f"Продвинуться в цели: {broken_goal}") == (
        f"Продвинуться в цели: {goal}"
    )
    assert repair_mojibake_text(f"Вы обозначили «{broken_goal}» как приоритет") == (
        f"Вы обозначили «{goal}» как приоритет"
    )
    short_goal = _legacy_decode("Я дизайнер")
    assert repair_mojibake_text(f"Продвинуться в цели: {short_goal}") == (
        "Продвинуться в цели: Я дизайнер"
    )


def test_repair_mojibake_text_supports_windows_1252() -> None:
    original = "Завершить макет"
    broken = original.encode("utf-8").decode("cp1252")

    assert "—" in broken
    assert repair_mojibake_text(broken) == original


def test_repair_mojibake_json_repairs_keys_and_nested_values() -> None:
    original = {"Цель": ["Русский текст", {"Описание": "Сделать проект"}]}
    broken = _corrupt_strings(original)

    assert repair_mojibake_json(broken) == original


@pytest.mark.parametrize("correct_first", [False, True])
def test_repair_mojibake_json_never_drops_colliding_key_values(
    correct_first: bool,
) -> None:
    correct = "Цель"
    broken = _legacy_decode(correct)
    pairs = [(correct, 2), (broken, 1)] if correct_first else [(broken, 1), (correct, 2)]

    repaired = repair_mojibake_json(dict(pairs))

    assert repaired == dict(pairs)
    assert len(repaired) == 2


def test_failed_backup_copy_cannot_leave_a_partial_final_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "profile.json"
    original = json.dumps({"goal": _legacy_decode("Завершить макет")}, ensure_ascii=False)
    path.write_text(original, encoding="utf-8")
    backup = path.with_name(f"{path.name}.before-encoding-repair")
    real_copy = encoding_recovery.shutil.copy2

    def interrupted_copy(_source: Path, target: Path) -> None:
        target.write_bytes(b"partial")
        raise OSError("disk full")

    monkeypatch.setattr(encoding_recovery.shutil, "copy2", interrupted_copy)
    assert repair_json_file(path) is False
    assert path.read_text(encoding="utf-8") == original
    assert not backup.exists()
    assert not list(tmp_path.glob(".*.tmp"))

    monkeypatch.setattr(encoding_recovery.shutil, "copy2", real_copy)
    assert repair_json_file(path) is True
    assert backup.read_text(encoding="utf-8") == original


def test_bootstrap_repairs_legacy_windows_state_without_reonboarding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    goal = "Завершить проект"
    context = "Работаю над приложением"
    blocker = "Мало свободного времени"
    monkeypatch.chdir(tmp_path)
    dispatch(
        {
            "action": "guided_onboard",
            "user_id": "default",
            "locale": "ru",
            "payload": {
                "display_name": "Иван",
                "current_context": context,
                "desired_change": f"Хочу {goal.lower()}",
                "friction": blocker,
                "focus_minutes": 30,
            },
        }
    )
    app = LumenApplication(tmp_path)
    workspace = UserWorkspace.from_root(tmp_path, "default")
    state_paths = (
        workspace.profile_path,
        workspace.onboarding_context_path,
        workspace.missions_path,
        workspace.work_sessions_path,
    )
    corrupted_inputs = (goal, goal.lower(), context, blocker)
    for path in state_paths:
        _corrupt_selected_in_file(path, corrupted_inputs)

    recovered = app.bootstrap("default", locale="ru")

    assert recovered["initialized"] is True
    dashboard = recovered["dashboard"]
    assert dashboard["user"]["display_name"] == "Иван"
    assert goal in dashboard["user"]["priorities"]
    assert goal in dashboard["today"]["title"]
    assert "Рџ" not in json.dumps(dashboard, ensure_ascii=False)
    saved_context = load_onboarding_context(workspace.onboarding_context_path)
    assert saved_context is not None
    assert saved_context["answers"]["current_context"] == context
    assert saved_context["answers"]["friction"] == blocker
    assert all(
        path.with_name(f"{path.name}.before-encoding-repair").is_file()
        for path in state_paths
    )
