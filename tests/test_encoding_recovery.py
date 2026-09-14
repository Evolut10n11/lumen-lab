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
    repair_workspace_json,
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


def test_single_marker_text_is_unchanged_without_independent_evidence() -> None:
    diagnostic = "Diagnose Ã© rendering"

    assert repair_mojibake_text(diagnostic) == diagnostic
    assert repair_mojibake_json({"note": diagnostic}) == {"note": diagnostic}


def test_workspace_evidence_allows_short_fragment_repair_across_files(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "profile.json"
    context = tmp_path / "onboarding_context.json"
    profile.write_text(
        json.dumps(
            {
                "goal": _legacy_decode("Я"),
                "letters": [_legacy_decode("Р"), _legacy_decode("С")],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    context.write_text(
        json.dumps({"context": _legacy_decode("Работаю дизайнером")}, ensure_ascii=False),
        encoding="utf-8",
    )

    repaired = repair_workspace_json(tmp_path)

    assert set(repaired) == {profile, context}
    repaired_profile = json.loads(profile.read_text(encoding="utf-8"))
    assert repaired_profile["goal"] == "Я"
    assert repaired_profile["letters"] == ["Р", "С"]
    assert json.loads(context.read_text(encoding="utf-8"))["context"] == (
        "Работаю дизайнером"
    )


def test_v021_backup_evidence_repairs_short_fragment_left_in_live_state(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "profile.json"
    live = {"goal": _legacy_decode("Я"), "context": "Работаю дизайнером"}
    original = {
        "goal": _legacy_decode("Я"),
        "context": _legacy_decode("Работаю дизайнером"),
    }
    profile.write_text(json.dumps(live, ensure_ascii=False), encoding="utf-8")
    backup = profile.with_name(f"{profile.name}.before-encoding-repair")
    backup.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")

    assert repair_workspace_json(tmp_path) == (profile,)
    assert json.loads(profile.read_text(encoding="utf-8")) == {
        "goal": "Я",
        "context": "Работаю дизайнером",
    }
    assert json.loads(backup.read_text(encoding="utf-8")) == original


def test_new_backup_evidence_invalidates_unchanged_workspace_cache(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "profile.json"
    live = {"goal": _legacy_decode("Я"), "context": "Работаю дизайнером"}
    profile.write_text(json.dumps(live, ensure_ascii=False), encoding="utf-8")

    assert repair_workspace_json(tmp_path) == ()

    backup = profile.with_name(f"{profile.name}.before-encoding-repair")
    backup.write_text(
        json.dumps(
            {"context": _legacy_decode("Работаю дизайнером")},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert repair_workspace_json(tmp_path) == (profile,)
    assert json.loads(profile.read_text(encoding="utf-8"))["goal"] == "Я"


def test_repair_mojibake_text_supports_windows_1252() -> None:
    original = "Завершить макет"
    broken = original.encode("utf-8").decode("cp1252")

    assert "—" in broken
    assert repair_mojibake_text(broken) == original


def test_repair_mojibake_json_repairs_keys_and_nested_values() -> None:
    original = {"Цель": ["Русский текст", {"Описание": "Сделать проект"}]}
    broken = _corrupt_strings(original)

    assert repair_mojibake_json(broken) == original


def test_workspace_evidence_does_not_rewrite_valid_quoted_letters() -> None:
    payload = {
        "legitimate": ["Буква «Р»", "Выберите «С»"],
        "broken": _legacy_decode("Работаю дизайнером"),
    }

    assert repair_mojibake_json(payload) == {
        "legitimate": ["Буква «Р»", "Выберите «С»"],
        "broken": "Работаю дизайнером",
    }


@pytest.mark.parametrize(
    "healthy",
    (
        "Температура 20 С°",
        "Марка «Р®»",
        "Обозначение Р°",
        "Коэффициент Рµ",
    ),
)
def test_workspace_evidence_does_not_rewrite_symbol_units(healthy: str) -> None:
    payload = {
        "healthy": healthy,
        "broken": _legacy_decode("Работаю дизайнером"),
    }

    assert repair_mojibake_json(payload)["healthy"] == healthy


def test_many_fragments_repair_in_one_idempotent_call_without_key_loss() -> None:
    fragment = _legacy_decode("цель")
    original = "ж".join([fragment] * 4)
    once_partial = "ж".join(["цель", fragment, fragment, fragment])
    twice_partial = "ж".join(["цель", "цель", fragment, fragment])
    expected = "ж".join(["цель"] * 4)

    assert repair_mojibake_text(original) == expected
    assert repair_mojibake_text(repair_mojibake_text(original)) == expected
    repaired = repair_mojibake_json(
        {original: "original", once_partial: "once", twice_partial: "twice"}
    )
    assert repaired == {
        original: "original",
        once_partial: "once",
        twice_partial: "twice",
    }


def test_fragment_detection_work_is_linear_for_long_healthy_marker_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "С" * 1600
    calls = 0
    real_decode_unit = encoding_recovery._decode_unit

    def counted_decode_unit(
        value: str,
        start: int,
        encoding: str,
    ) -> tuple[int, str] | None:
        nonlocal calls
        calls += 1
        return real_decode_unit(value, start, encoding)

    monkeypatch.setattr(encoding_recovery, "_decode_unit", counted_decode_unit)

    assert repair_mojibake_text(text) == text
    assert calls <= len(text) * len(encoding_recovery._LEGACY_ENCODINGS)


def test_rejected_reversible_run_is_not_rescanned_quadratically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = _legacy_decode("Р" * 1600)
    calls = 0
    real_decode_unit = encoding_recovery._decode_unit

    def counted_decode_unit(
        value: str,
        start: int,
        encoding: str,
    ) -> tuple[int, str] | None:
        nonlocal calls
        calls += 1
        return real_decode_unit(value, start, encoding)

    monkeypatch.setattr(encoding_recovery, "_decode_unit", counted_decode_unit)

    assert repair_mojibake_text(text) == text
    assert calls <= len(text) * len(encoding_recovery._LEGACY_ENCODINGS)


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
    real_replace = encoding_recovery.os.replace

    def interrupted_replace(source: Path, target: Path) -> None:
        if target == backup:
            raise OSError("disk full")
        real_replace(source, target)

    monkeypatch.setattr(encoding_recovery.os, "replace", interrupted_replace)
    assert repair_json_file(path) is False
    assert path.read_text(encoding="utf-8") == original
    assert not backup.exists()
    assert not list(tmp_path.glob(".*.tmp"))

    monkeypatch.setattr(encoding_recovery.os, "replace", real_replace)
    assert repair_json_file(path) is True
    assert backup.read_text(encoding="utf-8") == original


def test_existing_partial_backup_is_replaced_before_source_repair(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    original = json.dumps({"goal": _legacy_decode("Завершить макет")}, ensure_ascii=False)
    path.write_text(original, encoding="utf-8")
    backup = path.with_name(f"{path.name}.before-encoding-repair")
    backup.write_bytes(b"partial")

    assert repair_json_file(path) is True

    assert backup.read_text(encoding="utf-8") == original
    assert json.loads(path.read_text(encoding="utf-8"))["goal"] == "Завершить макет"


def test_existing_valid_backup_is_immutable_and_new_source_gets_snapshot(
    tmp_path: Path,
) -> None:
    path = tmp_path / "profile.json"
    original_backup = json.dumps(
        {"goal": _legacy_decode("Первоначальная цель")},
        ensure_ascii=False,
    ).encode()
    current_source = json.dumps(
        {"goal": _legacy_decode("Следующая цель")},
        ensure_ascii=False,
    ).encode()
    path.write_bytes(current_source)
    backup = path.with_name(f"{path.name}.before-encoding-repair")
    backup.write_bytes(original_backup)

    assert repair_json_file(path) is True

    assert backup.read_bytes() == original_backup
    snapshots = list(tmp_path.glob(f"{backup.name}.*"))
    assert len(snapshots) == 1
    assert snapshots[0].read_bytes() == current_source
    assert json.loads(path.read_text(encoding="utf-8"))["goal"] == "Следующая цель"


def test_temporarily_unreadable_backup_is_never_replaced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "profile.json"
    source = json.dumps(
        {"goal": _legacy_decode("Следующая цель")},
        ensure_ascii=False,
    ).encode()
    path.write_bytes(source)
    backup = path.with_name(f"{path.name}.before-encoding-repair")
    original_backup = json.dumps(
        {"goal": _legacy_decode("Первоначальная цель")},
        ensure_ascii=False,
    ).encode()
    backup.write_bytes(original_backup)
    real_read_bytes = Path.read_bytes

    def fail_backup_read(candidate: Path) -> bytes:
        if candidate == backup:
            raise OSError("temporarily unreadable")
        return real_read_bytes(candidate)

    monkeypatch.setattr(Path, "read_bytes", fail_backup_read)

    assert repair_json_file(path) is False
    assert real_read_bytes(backup) == original_backup
    assert real_read_bytes(path) == source


def test_source_change_before_final_identity_check_aborts_repair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "profile.json"
    stale = {"goal": _legacy_decode("Завершить макет"), "new_edit": False}
    newer = {"goal": _legacy_decode("Завершить макет"), "new_edit": True}
    path.write_text(json.dumps(stale, ensure_ascii=False), encoding="utf-8")
    real_backup = encoding_recovery._backup_original

    def save_during_recovery(backup: Path, source_bytes: bytes) -> None:
        real_backup(backup, source_bytes)
        path.write_text(json.dumps(newer, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(encoding_recovery, "_backup_original", save_during_recovery)

    assert repair_json_file(path) is False
    assert json.loads(path.read_text(encoding="utf-8")) == newer


def test_workspace_retries_after_transient_repair_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps({"goal": _legacy_decode("Завершить макет")}, ensure_ascii=False),
        encoding="utf-8",
    )
    real_backup = encoding_recovery._backup_original

    def fail_backup(_backup: Path, _source_bytes: bytes) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(encoding_recovery, "_backup_original", fail_backup)
    assert repair_workspace_json(tmp_path) == ()
    assert _legacy_decode("Завершить макет") in profile.read_text(encoding="utf-8")

    monkeypatch.setattr(encoding_recovery, "_backup_original", real_backup)
    assert repair_workspace_json(tmp_path) == (profile,)
    assert json.loads(profile.read_text(encoding="utf-8"))["goal"] == "Завершить макет"


def test_unchanged_workspace_is_not_scanned_repeatedly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text('{"goal": "Готово"}', encoding="utf-8")

    assert repair_workspace_json(tmp_path) == ()

    def unexpected_scan(*_args: Any, **_kwargs: Any) -> bool:
        raise AssertionError("unchanged workspace was scanned again")

    monkeypatch.setattr(encoding_recovery, "_repair_json_file_locked", unexpected_scan)
    assert repair_workspace_json(tmp_path) == ()


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
