from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .localization import is_russian, normalize_locale
from .profile import normalized_label

ONBOARDING_CONTEXT_VERSION = 1
ALLOWED_FOCUS_MINUTES = (15, 30, 60)
_MAX_ANSWER_LENGTH = 1200

_PREFIXES = (
    r"i\s+(?:really\s+)?(?:want|need|would\s+like)\s+to\s+",
    r"i(?:'m|\s+am)\s+trying\s+to\s+",
    r"my\s+goal\s+is\s+(?:to\s+)?",
    r"я\s+(?:очень\s+)?хочу\s+",
    r"хочу\s+",
    r"мне\s+нужно\s+",
    r"я\s+пытаюсь\s+",
    r"моя\s+цель\s*(?:[-—:]\s*)?",
)
_GOAL_PREFIX_RE = re.compile(rf"^(?:{'|'.join(_PREFIXES)})", re.IGNORECASE)

_VAGUE_GOAL_MARKERS = (
    "стало лучше",
    "всё стало лучше",
    "все стало лучше",
    "наладить жизнь",
    "разобраться в жизни",
    "что-то изменить",
    "что то изменить",
    "better",
    "improve things",
    "improve my life",
    "figure things out",
)

_CONTEXT_THEMES: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    (
        "career",
        (
            "собесед",
            "ваканс",
            "резюме",
            "карьер",
            "разработ",
            "программист",
            "инженер",
            "interview",
            "vacancy",
            "resume",
            "career",
            "developer",
            "engineer",
        ),
        "карьерная подготовка и доказательства навыков",
        "career preparation and visible proof of skill",
    ),
    (
        "study",
        (
            "универ",
            "сесс",
            "экзам",
            "диплом",
            "курсов",
            "учусь",
            "university",
            "study",
            "exam",
            "thesis",
            "coursework",
        ),
        "ближайший учебный дедлайн",
        "the nearest study deadline",
    ),
    (
        "project",
        (
            "pet project",
            "side project",
            "проект",
            "стартап",
            "продукт",
            "запуск",
            "project",
            "startup",
            "product",
            "launch",
            "ship",
        ),
        "один пользовательский результат в текущем проекте",
        "one user-visible outcome in the current project",
    ),
    (
        "creative",
        (
            "рис",
            "иллюстрац",
            "публиков",
            "творч",
            "контент",
            "блог",
            "музык",
            "draw",
            "illustr",
            "publish",
            "creative",
            "content",
            "art",
            "music",
        ),
        "публикация одной законченной творческой работы",
        "publishing one finished creative piece",
    ),
    (
        "routine",
        (
            "режим",
            "сон",
            "энерг",
            "бодр",
            "двига",
            "спорт",
            "устал",
            "routine",
            "sleep",
            "energy",
            "exercise",
            "movement",
            "tired",
        ),
        "небольшой устойчивый эксперимент с режимом",
        "a small sustainable routine experiment",
    ),
)


def _clean_answer(value: str, name: str, *, required: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    cleaned = " ".join(value.strip().split())
    if required and not cleaned:
        raise ValueError(f"{name} must be a non-empty string")
    if len(cleaned) > _MAX_ANSWER_LENGTH:
        raise ValueError(f"{name} must be {_MAX_ANSWER_LENGTH} characters or fewer")
    return cleaned


def _validated_focus_minutes(value: int) -> int:
    if isinstance(value, bool) or value not in ALLOWED_FOCUS_MINUTES:
        allowed = ", ".join(str(item) for item in ALLOWED_FOCUS_MINUTES)
        raise ValueError(f"focus_minutes must be one of: {allowed}")
    return value


def _looks_russian(value: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", value))


def _is_vague_goal(value: str) -> bool:
    normalized = normalized_label(value)
    words = normalized.split()
    if len(words) > 7:
        return False
    return any(marker in normalized for marker in _VAGUE_GOAL_MARKERS)


def _context_theme(context: str, primary_goal: str) -> str | None:
    combined = f"{context} {primary_goal}".casefold()
    russian = _looks_russian(combined)
    best: tuple[int, str, str] | None = None
    for _name, keywords, russian_label, english_label in _CONTEXT_THEMES:
        score = sum(1 for keyword in keywords if keyword in combined)
        if score <= 0:
            continue
        candidate = (score, russian_label, english_label)
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best is None:
        return None
    return best[1] if russian else best[2]


def goal_label(value: str) -> str:
    """Turn a normal first-person answer into a concise goal label when possible."""
    cleaned = _clean_answer(value, "desired_change")
    label = _GOAL_PREFIX_RE.sub("", cleaned, count=1).strip(" .,!?:;\"'“”«»")
    if not label:
        label = cleaned
    if _is_vague_goal(label):
        return (
            "Уточнить, что именно должно измениться"
            if _looks_russian(cleaned)
            else "Clarify what should actually change"
        )
    if label and label[0].islower():
        label = label[0].upper() + label[1:]
    return label


def guided_profile_inputs(
    *,
    current_context: str,
    desired_change: str,
    friction: str = "",
    focus_minutes: int = 30,
) -> dict[str, Any]:
    """Infer conservative starter profile inputs from a short first-run conversation."""
    context = _clean_answer(current_context, "current_context")
    change = _clean_answer(desired_change, "desired_change")
    blocker = _clean_answer(friction, "friction", required=False)
    focus_minutes = _validated_focus_minutes(focus_minutes)

    primary_goal = goal_label(change)
    theme = _context_theme(context, primary_goal)
    interests: tuple[str, ...] = ()
    if theme and normalized_label(theme) != normalized_label(primary_goal):
        interests = (theme,)

    return {
        "priorities": {primary_goal: 10},
        "interests": interests,
        "constraints": (blocker,) if blocker else (),
        "focus_minutes": focus_minutes,
    }


def onboarding_context_payload(
    *,
    current_context: str,
    desired_change: str,
    friction: str = "",
    focus_minutes: int = 30,
    locale: str = "en",
) -> dict[str, Any]:
    """Persist raw answers separately from the profile so later learning can revise hypotheses."""
    locale = normalize_locale(locale)
    inputs = guided_profile_inputs(
        current_context=current_context,
        desired_change=desired_change,
        friction=friction,
        focus_minutes=focus_minutes,
    )
    context = _clean_answer(current_context, "current_context")
    change = _clean_answer(desired_change, "desired_change")
    blocker = _clean_answer(friction, "friction", required=False)
    goal = next(iter(inputs["priorities"]))

    if is_russian(locale):
        labels = {
            "primary_goal": "Что вы хотите изменить",
            "current_context": "Что сейчас занимает ваше внимание",
            "focus_window": "Реалистичное время на фокус",
            "friction": "Что обычно мешает",
        }
        focus_value = f"{focus_minutes} минут"
    else:
        labels = {
            "primary_goal": "What you want to change",
            "current_context": "What has your attention now",
            "focus_window": "Realistic focus window",
            "friction": "What tends to get in the way",
        }
        focus_value = f"{focus_minutes} minutes"

    hypotheses: list[dict[str, Any]] = [
        {
            "key": "primary_goal",
            "label": labels["primary_goal"],
            "value": goal,
            "confidence": 0.78,
            "source": "first_run_explicit_goal",
        },
        {
            "key": "current_context",
            "label": labels["current_context"],
            "value": context,
            "confidence": 0.86,
            "source": "first_run_explicit_context",
        },
        {
            "key": "focus_window",
            "label": labels["focus_window"],
            "value": focus_value,
            "confidence": 0.95,
            "source": "first_run_explicit_choice",
        },
    ]
    if blocker:
        hypotheses.append(
            {
                "key": "friction",
                "label": labels["friction"],
                "value": blocker,
                "confidence": 0.82,
                "source": "first_run_explicit_constraint",
            }
        )

    return {
        "version": ONBOARDING_CONTEXT_VERSION,
        "source": "conversation",
        "locale": locale,
        "answers": {
            "current_context": context,
            "desired_change": change,
            "friction": blocker or None,
            "focus_minutes": focus_minutes,
        },
        "hypotheses": hypotheses,
        "average_confidence": round(
            sum(item["confidence"] for item in hypotheses) / len(hypotheses),
            2,
        ),
    }


def save_onboarding_context(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_onboarding_context(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("onboarding context must contain a JSON object")
    return raw


def apply_focus_minutes(path: Path, focus_minutes: int) -> None:
    """Tune generated work sessions to the focus window chosen in first-run setup."""
    focus_minutes = _validated_focus_minutes(focus_minutes)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("work sessions state must contain a JSON list")
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("work session entries must be JSON objects")
        item["focus_minutes"] = focus_minutes
    path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
