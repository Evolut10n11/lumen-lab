import json
from pathlib import Path

import pytest

from lumen_lab.mission_radar import Mission
from lumen_lab.work_session import (
    WorkSessionTemplate,
    choose_mission,
    load_progress,
    load_templates,
    mark_step_done,
    session_snapshot,
    template_for,
)
from lumen_lab.work_session_cli import main


def mission(identifier: str, impact: int = 8, status: str = "active") -> Mission:
    return Mission(
        id=identifier,
        title=f"Mission {identifier}",
        why_now="Because now.",
        next_action="Do the next thing.",
        impact=impact,
        urgency=8,
        leverage=8,
        momentum=8,
        effort=5,
        risk=2,
        status=status,
    )


def template(identifier: str) -> WorkSessionTemplate:
    return WorkSessionTemplate(
        mission_id=identifier,
        focus_minutes=60,
        steps=("First", "Second", "Third"),
        definition_of_done="All three are complete.",
    )


def write_missions(path: Path, items: list[Mission]) -> None:
    payload = []
    for item in items:
        data = item.to_dict()
        data.pop("score")
        payload.append(data)
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_templates(path: Path, items: list[WorkSessionTemplate]) -> None:
    payload = [
        {
            "mission_id": item.mission_id,
            "focus_minutes": item.focus_minutes,
            "steps": list(item.steps),
            "definition_of_done": item.definition_of_done,
        }
        for item in items
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_choose_mission_uses_radar_ranking() -> None:
    low = mission("low", impact=5)
    high = mission("high", impact=10)
    assert choose_mission([low, high]).id == "high"


def test_explicit_mission_must_be_active() -> None:
    with pytest.raises(ValueError, match="active mission not found"):
        choose_mission([mission("paused", status="paused")], "paused")


def test_template_validation_rejects_empty_steps() -> None:
    bad = WorkSessionTemplate(
        mission_id="m",
        focus_minutes=60,
        steps=(),
        definition_of_done="Done.",
    )
    with pytest.raises(ValueError, match="at least one step"):
        bad.validate()


def test_load_templates_rejects_duplicate_mission_ids(tmp_path: Path) -> None:
    path = tmp_path / "templates.json"
    write_templates(path, [template("same"), template("same")])
    with pytest.raises(ValueError, match="duplicate"):
        load_templates(path)


def test_template_for_requires_matching_template() -> None:
    with pytest.raises(ValueError, match="template not found"):
        template_for([template("one")], "two")


def test_snapshot_tracks_progress_deterministically() -> None:
    item = mission("m")
    snap = session_snapshot(item, template("m"), {"m": [3, 1]})
    assert [step["done"] for step in snap["steps"]] == [True, False, True]
    assert snap["progress"] == {"completed": 2, "total": 3, "percent": 67}


def test_mark_done_persists_local_progress(tmp_path: Path) -> None:
    path = tmp_path / ".lumen" / "work_progress.json"
    progress = mark_step_done(path, "m", 2, 3)
    assert progress == {"m": [2]}
    assert load_progress(path) == {"m": [2]}


def test_mark_done_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    mark_step_done(path, "m", 1, 3)
    mark_step_done(path, "m", 1, 3)
    assert load_progress(path) == {"m": [1]}


def test_mark_done_rejects_invalid_step(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="between 1 and 3"):
        mark_step_done(tmp_path / "progress.json", "m", 4, 3)


def test_read_only_cli_does_not_create_progress(tmp_path: Path, capsys) -> None:
    missions_path = tmp_path / "missions.json"
    templates_path = tmp_path / "templates.json"
    progress_path = tmp_path / "runtime" / "progress.json"
    write_missions(missions_path, [mission("m")])
    write_templates(templates_path, [template("m")])

    code = main(
        [
            "--missions",
            str(missions_path),
            "--templates",
            str(templates_path),
            "--progress",
            str(progress_path),
        ]
    )

    assert code == 0
    assert "Lumen Work Session" in capsys.readouterr().out
    assert not progress_path.exists()


def test_cli_done_updates_only_progress_file(tmp_path: Path) -> None:
    missions_path = tmp_path / "missions.json"
    templates_path = tmp_path / "templates.json"
    progress_path = tmp_path / "runtime" / "progress.json"
    write_missions(missions_path, [mission("m")])
    write_templates(templates_path, [template("m")])
    before_missions = missions_path.read_bytes()
    before_templates = templates_path.read_bytes()

    code = main(
        [
            "--missions",
            str(missions_path),
            "--templates",
            str(templates_path),
            "--progress",
            str(progress_path),
            "--done",
            "2",
        ]
    )

    assert code == 0
    assert load_progress(progress_path) == {"m": [2]}
    assert missions_path.read_bytes() == before_missions
    assert templates_path.read_bytes() == before_templates


def test_json_output_is_machine_readable(tmp_path: Path, capsys) -> None:
    missions_path = tmp_path / "missions.json"
    templates_path = tmp_path / "templates.json"
    progress_path = tmp_path / "progress.json"
    write_missions(missions_path, [mission("m")])
    write_templates(templates_path, [template("m")])

    code = main(
        [
            "--missions",
            str(missions_path),
            "--templates",
            str(templates_path),
            "--progress",
            str(progress_path),
            "--json",
        ]
    )

    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["mission_id"] == "m"
    assert data["steps"][0] == {"number": 1, "text": "First", "done": False}
