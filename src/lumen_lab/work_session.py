from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .mission_radar import Mission, ranked_missions

DEFAULT_TEMPLATES_PATH = Path("state/work_sessions.json")
DEFAULT_PROGRESS_PATH = Path(".lumen/work_progress.json")


@dataclass(frozen=True)
class WorkSessionTemplate:
    mission_id: str
    focus_minutes: int
    steps: tuple[str, ...]
    definition_of_done: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> WorkSessionTemplate:
        expected = {"mission_id", "focus_minutes", "steps", "definition_of_done"}
        unknown = set(raw) - expected
        missing = expected - set(raw)
        if unknown:
            raise ValueError(f"unknown work-session fields: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing work-session fields: {', '.join(sorted(missing))}")

        steps = raw["steps"]
        if not isinstance(steps, list):
            raise ValueError("work-session steps must be a JSON list")
        template = cls(
            mission_id=raw["mission_id"],
            focus_minutes=raw["focus_minutes"],
            steps=tuple(steps),
            definition_of_done=raw["definition_of_done"],
        )
        template.validate()
        return template

    def validate(self) -> None:
        if not isinstance(self.mission_id, str) or not self.mission_id.strip():
            raise ValueError("work-session mission_id must be a non-empty string")
        if isinstance(self.focus_minutes, bool) or not isinstance(self.focus_minutes, int):
            raise ValueError("work-session focus_minutes must be an integer")
        if not 15 <= self.focus_minutes <= 180:
            raise ValueError("work-session focus_minutes must be between 15 and 180")
        if not self.steps:
            raise ValueError("work-session must contain at least one step")
        if len(self.steps) > 12:
            raise ValueError("work-session must contain at most 12 steps")
        for step in self.steps:
            if not isinstance(step, str) or not step.strip():
                raise ValueError("work-session steps must be non-empty strings")
        if not isinstance(self.definition_of_done, str) or not self.definition_of_done.strip():
            raise ValueError("work-session definition_of_done must be a non-empty string")


def load_templates(path: Path = DEFAULT_TEMPLATES_PATH) -> list[WorkSessionTemplate]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("work-session state must contain a JSON list")

    templates: list[WorkSessionTemplate] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("work-session entries must be JSON objects")
        template = WorkSessionTemplate.from_dict(item)
        if template.mission_id in seen:
            raise ValueError(f"duplicate work-session mission_id: {template.mission_id}")
        seen.add(template.mission_id)
        templates.append(template)
    return templates


def load_progress(path: Path = DEFAULT_PROGRESS_PATH) -> dict[str, list[int]]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("work progress must contain a JSON object")

    progress: dict[str, list[int]] = {}
    for mission_id, completed in raw.items():
        if not isinstance(mission_id, str) or not mission_id.strip():
            raise ValueError("work progress mission IDs must be non-empty strings")
        if not isinstance(completed, list):
            raise ValueError(f"work progress for {mission_id} must be a JSON list")
        invalid_item = any(
            isinstance(item, bool) or not isinstance(item, int) or item < 1
            for item in completed
        )
        if invalid_item:
            raise ValueError(
                f"work progress for {mission_id} must contain positive step numbers"
            )
        if len(set(completed)) != len(completed):
            raise ValueError(f"work progress for {mission_id} contains duplicate step numbers")
        progress[mission_id] = sorted(completed)
    return progress


def choose_mission(missions: list[Mission], mission_id: str | None = None) -> Mission:
    active = ranked_missions(missions)
    if mission_id is None:
        if not active:
            raise ValueError("no active missions")
        return active[0]

    for mission in active:
        if mission.id == mission_id:
            return mission
    raise ValueError(f"active mission not found: {mission_id}")


def template_for(
    templates: list[WorkSessionTemplate], mission_id: str
) -> WorkSessionTemplate:
    for template in templates:
        if template.mission_id == mission_id:
            return template
    raise ValueError(f"work-session template not found for mission: {mission_id}")


def validate_progress_for_template(
    completed: list[int], template: WorkSessionTemplate
) -> None:
    step_count = len(template.steps)
    invalid = [number for number in completed if number > step_count]
    if invalid:
        joined = ", ".join(str(number) for number in invalid)
        raise ValueError(
            f"progress contains invalid step numbers for {template.mission_id}: {joined}"
        )


def mark_step_done(
    path: Path,
    mission_id: str,
    step_number: int,
    step_count: int,
) -> dict[str, list[int]]:
    if isinstance(step_number, bool) or not 1 <= step_number <= step_count:
        raise ValueError(f"step must be between 1 and {step_count}")

    progress = load_progress(path)
    completed = set(progress.get(mission_id, []))
    completed.add(step_number)
    progress[mission_id] = sorted(completed)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(progress, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return progress


def session_snapshot(
    mission: Mission,
    template: WorkSessionTemplate,
    progress: dict[str, list[int]],
) -> dict[str, Any]:
    completed = progress.get(mission.id, [])
    validate_progress_for_template(completed, template)
    completed_set = set(completed)
    total = len(template.steps)
    done_count = len(completed_set)
    percent = round(done_count / total * 100) if total else 0

    return {
        "mission_id": mission.id,
        "title": mission.title,
        "why_now": mission.why_now,
        "score": mission.score,
        "focus_minutes": template.focus_minutes,
        "steps": [
            {"number": number, "text": text, "done": number in completed_set}
            for number, text in enumerate(template.steps, start=1)
        ],
        "progress": {"completed": done_count, "total": total, "percent": percent},
        "definition_of_done": template.definition_of_done,
    }
