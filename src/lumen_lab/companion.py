from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .localization import is_russian, normalize_locale
from .mission_radar import Mission
from .state_io import write_json_atomic
from .work_session import WorkSessionTemplate

COMPANION_SCHEMA_VERSION = 1
STEP_XP = 5
MISSION_XP = 25
XP_PER_LEVEL = 100
_EVENT_XP = {"step_completed": STEP_XP, "mission_completed": MISSION_XP}


@dataclass(frozen=True, slots=True)
class CompanionCharacter:
    id: str
    name_en: str
    name_ru: str
    personality_en: str
    personality_ru: str
    accent: str
    symbol: str
    lines_en: dict[str, str]
    lines_ru: dict[str, str]


CHARACTERS = (
    CompanionCharacter(
        id="lumi",
        name_en="Lumi",
        name_ru="Люми",
        personality_en="Warm and curious",
        personality_ru="Тёплая и любознательная",
        accent="#d7ff68",
        symbol="✦",
        lines_en={
            "greeting": "I’ll keep the next step clear and celebrate the real ones.",
            "step_completed": "Nice. One real step is behind us.",
            "mission_completed": "You closed the loop. That deserves a small celebration.",
        },
        lines_ru={
            "greeting": "Я помогу видеть следующий шаг и замечать настоящий прогресс.",
            "step_completed": "Отлично. Один настоящий шаг уже позади.",
            "mission_completed": "Цикл завершён. Это стоит маленького праздника.",
        },
    ),
    CompanionCharacter(
        id="kiro",
        name_en="Kiro",
        name_ru="Киро",
        personality_en="Direct and energetic",
        personality_ru="Прямой и энергичный",
        accent="#ff9d66",
        symbol="⚡",
        lines_en={
            "greeting": "Give me the target. We’ll turn it into movement.",
            "step_completed": "Step locked in. Keep the momentum.",
            "mission_completed": "Mission complete. Clear result, clean finish.",
        },
        lines_ru={
            "greeting": "Дай мне цель — превратим её в движение.",
            "step_completed": "Шаг зафиксирован. Сохраняем темп.",
            "mission_completed": "Миссия закрыта. Чёткий результат, чистый финиш.",
        },
    ),
    CompanionCharacter(
        id="momo",
        name_en="Momo",
        name_ru="Момо",
        personality_en="Calm and encouraging",
        personality_ru="Спокойная и поддерживающая",
        accent="#b8a5ff",
        symbol="☾",
        lines_en={
            "greeting": "We can move gently and still move forward.",
            "step_completed": "That is enough for this step. Breathe, then continue.",
            "mission_completed": "You made it through. Let the result settle for a moment.",
        },
        lines_ru={
            "greeting": "Можно двигаться бережно и всё равно идти вперёд.",
            "step_completed": "Для этого шага достаточно. Выдохните и продолжайте.",
            "mission_completed": "Вы справились. Дайте результату немного улечься.",
        },
    ),
)
_CHARACTERS_BY_ID = {character.id: character for character in CHARACTERS}


@dataclass(frozen=True, slots=True)
class CompanionState:
    selected_character_id: str
    total_xp: int
    chapter: int
    processed_event_ids: tuple[str, ...]
    last_event_kind: str

    @classmethod
    def default(cls) -> CompanionState:
        return cls("lumi", 0, 1, (), "greeting")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CompanionState:
        expected = {
            "schema_version",
            "selected_character_id",
            "total_xp",
            "chapter",
            "processed_event_ids",
            "last_event_kind",
        }
        unknown = set(raw) - expected
        missing = expected - set(raw)
        if unknown:
            raise ValueError(f"unknown companion fields: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing companion fields: {', '.join(sorted(missing))}")
        if raw["schema_version"] != COMPANION_SCHEMA_VERSION:
            raise ValueError("unsupported companion schema version")
        selected = raw["selected_character_id"]
        if not isinstance(selected, str) or selected not in _CHARACTERS_BY_ID:
            raise ValueError(f"unknown companion character: {selected}")
        total_xp = raw["total_xp"]
        if isinstance(total_xp, bool) or not isinstance(total_xp, int) or total_xp < 0:
            raise ValueError("companion total_xp must be a non-negative integer")
        chapter = raw["chapter"]
        if isinstance(chapter, bool) or not isinstance(chapter, int) or chapter < 1:
            raise ValueError("companion chapter must be a positive integer")
        event_ids = raw["processed_event_ids"]
        if not isinstance(event_ids, list) or not all(
            isinstance(item, str) and item for item in event_ids
        ):
            raise ValueError("companion processed_event_ids must contain non-empty strings")
        if len(set(event_ids)) != len(event_ids):
            raise ValueError("companion processed_event_ids contains duplicates")
        event_kind = raw["last_event_kind"]
        if not isinstance(event_kind, str) or event_kind not in {*_EVENT_XP, "greeting"}:
            raise ValueError(f"unsupported companion event kind: {event_kind}")
        return cls(selected, total_xp, chapter, tuple(event_ids), event_kind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": COMPANION_SCHEMA_VERSION,
            "selected_character_id": self.selected_character_id,
            "total_xp": self.total_xp,
            "chapter": self.chapter,
            "processed_event_ids": list(self.processed_event_ids),
            "last_event_kind": self.last_event_kind,
        }


def load_companion_state(path: Path) -> CompanionState:
    if not path.is_file():
        return CompanionState.default()
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("companion state must contain a JSON object")
    return CompanionState.from_dict(raw)


def _events_from_progress(
    missions: list[Mission],
    templates: list[WorkSessionTemplate],
    progress: dict[str, list[int]],
) -> list[tuple[str, str]]:
    step_counts = {template.mission_id: len(template.steps) for template in templates}
    events: list[tuple[str, str]] = []
    for mission in missions:
        completed = progress.get(mission.id, [])
        step_count = step_counts.get(mission.id, 0)
        for step in completed:
            if 1 <= step <= step_count:
                events.append((f"step:{mission.id}:{step}", "step_completed"))
        if mission.status == "done" and completed == list(range(1, step_count + 1)):
            events.append((f"mission:{mission.id}", "mission_completed"))
    return events


def synchronize_companion(
    path: Path,
    missions: list[Mission],
    templates: list[WorkSessionTemplate],
    progress: dict[str, list[int]],
) -> CompanionState:
    state = load_companion_state(path)
    processed = list(state.processed_event_ids)
    seen = set(processed)
    total_xp = state.total_xp
    last_event_kind = state.last_event_kind
    changed = False
    for event_id, event_kind in _events_from_progress(missions, templates, progress):
        event_id = f"chapter:{state.chapter}:{event_id}"
        if event_id in seen:
            continue
        seen.add(event_id)
        processed.append(event_id)
        total_xp += _EVENT_XP[event_kind]
        last_event_kind = event_kind
        changed = True
    if not changed:
        return state
    updated = CompanionState(
        selected_character_id=state.selected_character_id,
        total_xp=total_xp,
        chapter=state.chapter,
        processed_event_ids=tuple(processed),
        last_event_kind=last_event_kind,
    )
    write_json_atomic(path, updated.to_dict())
    return updated


def select_companion(path: Path, character_id: str) -> CompanionState:
    selected = character_id.strip().casefold()
    if selected not in _CHARACTERS_BY_ID:
        allowed = ", ".join(character.id for character in CHARACTERS)
        raise ValueError(f"companion character must be one of: {allowed}")
    state = load_companion_state(path)
    updated = CompanionState(
        selected_character_id=selected,
        total_xp=state.total_xp,
        chapter=state.chapter,
        processed_event_ids=state.processed_event_ids,
        last_event_kind="greeting",
    )
    write_json_atomic(path, updated.to_dict())
    return updated


def start_companion_chapter(path: Path) -> CompanionState:
    state = load_companion_state(path)
    updated = CompanionState(
        selected_character_id=state.selected_character_id,
        total_xp=state.total_xp,
        chapter=state.chapter + 1,
        processed_event_ids=state.processed_event_ids,
        last_event_kind="greeting",
    )
    write_json_atomic(path, updated.to_dict())
    return updated


def companion_payload(state: CompanionState, *, locale: str = "en") -> dict[str, Any]:
    russian = is_russian(normalize_locale(locale))
    selected = _CHARACTERS_BY_ID[state.selected_character_id]
    level = state.total_xp // XP_PER_LEVEL + 1
    level_start = (level - 1) * XP_PER_LEVEL
    level_progress = state.total_xp - level_start

    def character_payload(character: CompanionCharacter) -> dict[str, Any]:
        return {
            "id": character.id,
            "name": character.name_ru if russian else character.name_en,
            "personality": (
                character.personality_ru if russian else character.personality_en
            ),
            "accent": character.accent,
            "symbol": character.symbol,
            "access": "free",
            "selected": character.id == state.selected_character_id,
        }

    lines = selected.lines_ru if russian else selected.lines_en
    return {
        "selected": character_payload(selected),
        "characters": [character_payload(character) for character in CHARACTERS],
        "total_xp": state.total_xp,
        "level": level,
        "level_progress": level_progress,
        "level_target": XP_PER_LEVEL,
        "level_percent": round(level_progress / XP_PER_LEVEL * 100),
        "last_reaction": {
            "kind": state.last_event_kind,
            "message": lines[state.last_event_kind],
        },
    }
