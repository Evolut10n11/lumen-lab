from __future__ import annotations

import hashlib
from collections.abc import Iterable

from .localization import is_russian, normalize_locale
from .mission_radar import Mission, save_missions
from .profile import CandidateGenerationPolicy, Profile, normalized_label
from .state_io import write_json_atomic
from .work_session import WorkSessionTemplate
from .workspace import UserWorkspace


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = raw.strip()
        if not value:
            continue
        key = normalized_label(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return tuple(result)


def profile_payload(profile: Profile) -> dict[str, object]:
    return {
        "id": profile.id,
        "display_name": profile.display_name,
        "priorities": dict(profile.priorities),
        "skills": list(profile.skills),
        "interests": list(profile.interests),
        "constraints": list(profile.constraints),
        "preferred_stack": list(profile.preferred_stack),
        "risk_tolerance": profile.risk_tolerance,
        "candidate_generation_policy": {
            "mode": profile.candidate_generation_policy.mode,
            "allow_llm": profile.candidate_generation_policy.allow_llm,
            "max_candidates": profile.candidate_generation_policy.max_candidates,
        },
    }


def build_profile(
    *,
    user_id: str,
    display_name: str,
    priorities: dict[str, int],
    skills: Iterable[str] = (),
    interests: Iterable[str] = (),
    constraints: Iterable[str] = (),
    preferred_stack: Iterable[str] = (),
    risk_tolerance: int = 5,
    policy_mode: str = "reviewed",
    allow_llm: bool = False,
    max_candidates: int = 5,
) -> Profile:
    profile = Profile(
        id=user_id,
        display_name=display_name.strip(),
        priorities={key.strip(): value for key, value in priorities.items()},
        skills=_dedupe(skills),
        interests=_dedupe(interests),
        constraints=_dedupe(constraints),
        preferred_stack=_dedupe(preferred_stack),
        risk_tolerance=risk_tolerance,
        candidate_generation_policy=CandidateGenerationPolicy(
            mode=policy_mode,
            allow_llm=allow_llm,
            max_candidates=max_candidates,
        ),
    )
    profile.validate()
    return Profile.from_dict(profile_payload(profile))


def _mission_id(user_id: str, label: str, index: int) -> str:
    digest = hashlib.sha256(f"{user_id}:{label}:{index}".encode()).hexdigest()[:8]
    return f"personal-{index}-{digest}"


def starter_missions(profile: Profile, *, locale: str = "en") -> list[Mission]:
    """Create a small portfolio solely from the explicit user's profile."""
    if not profile.priorities:
        raise ValueError("at least one priority is required to create personalized missions")

    locale = normalize_locale(locale)
    russian = is_russian(locale)
    ordered_priorities = sorted(
        profile.priorities.items(),
        key=lambda item: (-item[1], normalized_label(item[0])),
    )
    primary, weight = ordered_priorities[0]
    interest = profile.interests[0] if profile.interests else None
    skill = profile.skills[0] if profile.skills else None
    safe_risk = max(1, min(profile.risk_tolerance, 4))

    if russian:
        primary_spec = (
            f"Продвинуться в цели: {primary}",
            (
                f"Вы обозначили «{primary}» как главный приоритет, поэтому сначала стоит "
                "получить конкретный результат именно здесь."
            ),
            (
                f"Определите один измеримый результат по цели «{primary}», который можно "
                "завершить или проверить в течение семи дней."
            ),
        )
    else:
        primary_spec = (
            f"Move {primary} forward",
            (
                f"You ranked {primary} at {weight}/10, so it should receive a concrete "
                "outcome before lower-priority work."
            ),
            (
                f"Define one measurable result for {primary} that can be completed or "
                "validated within seven days."
            ),
        )

    specs: list[tuple[str, str, str, tuple[str, ...], int, int, int, int, int, int]] = [
        (
            primary_spec[0],
            primary_spec[1],
            primary_spec[2],
            (primary,),
            max(6, weight),
            max(5, weight),
            8,
            7,
            4,
            safe_risk,
        )
    ]

    if interest:
        if russian:
            title = f"Связать «{interest}» с целью «{primary}»"
            why_now = (
                f"«{interest}» занимает ваше внимание, а «{primary}» — главный приоритет. "
                "Если связать их, можно одновременно сохранить мотивацию и получить полезный результат."
            )
            next_action = (
                f"Выберите небольшой эксперимент вокруг «{interest}», который даст конкретное "
                f"подтверждение прогресса по цели «{primary}»."
            )
        else:
            title = f"Connect {interest} to {primary}"
            why_now = (
                f"{interest} is an explicit interest and {primary} is your "
                "highest-weighted priority; connecting them can create motivation "
                "and useful evidence at the same time."
            )
            next_action = (
                f"Choose one small {interest} experiment that produces evidence "
                f"for {primary}."
            )
        specs.append(
            (
                title,
                why_now,
                next_action,
                (
                    (primary, interest)
                    if normalized_label(primary) != normalized_label(interest)
                    else (primary,)
                ),
                max(6, weight - 1),
                max(5, weight - 1),
                7,
                7,
                5,
                safe_risk,
            )
        )
    else:
        if russian:
            title = f"Создать видимый результат для цели «{primary}»"
            why_now = (
                f"«{primary}» сейчас главный приоритет. Прогресс полезнее, когда после него "
                "остаётся конкретный артефакт или измеримый результат."
            )
            next_action = (
                f"Выберите самый маленький видимый результат, который подтвердит прогресс по «{primary}», "
                "и определите критерии готовности."
            )
        else:
            title = f"Create visible evidence for {primary}"
            why_now = (
                f"Your profile makes {primary} the current leading priority, but "
                "progress becomes more useful when it leaves a concrete artifact "
                "or measurable result."
            )
            next_action = (
                "Pick the smallest visible artifact that would prove progress on "
                f"{primary} and define its acceptance criteria."
            )
        specs.append(
            (
                title,
                why_now,
                next_action,
                (primary,),
                max(6, weight - 1),
                max(5, weight - 1),
                7,
                6,
                5,
                safe_risk,
            )
        )

    if skill:
        if russian:
            title = f"Использовать {skill}, чтобы ускорить цель «{primary}»"
            why_now = (
                f"{skill} уже есть среди ваших навыков, поэтому его применение к цели «{primary}» "
                "снизит время на разгон и даст больше отдачи от того, что вы уже умеете."
            )
            next_action = (
                f"Найдите одну задачу по цели «{primary}», где {skill} сильнее всего уменьшает "
                "неопределённость, и выполните первый ограниченный кусок."
            )
        else:
            title = f"Use {skill} to accelerate {primary}"
            why_now = (
                f"{skill} is already in your skill set, so using it against "
                f"{primary} should reduce ramp-up cost and turn existing capability "
                "into leverage."
            )
            next_action = (
                f"Identify one task for {primary} where {skill} removes the most "
                "uncertainty, then complete the first bounded slice."
            )
        specs.append(
            (
                title,
                why_now,
                next_action,
                (
                    (primary, skill)
                    if normalized_label(primary) != normalized_label(skill)
                    else (primary,)
                ),
                max(6, weight - 1),
                max(4, weight - 2),
                9,
                8,
                4,
                safe_risk,
            )
        )
    elif len(ordered_priorities) > 1:
        secondary, secondary_weight = ordered_priorities[1]
        if russian:
            title = f"Совместить «{primary}» и «{secondary}»"
            why_now = (
                f"«{primary}» ведёт среди приоритетов, но «{secondary}» тоже важна. Вместо двух "
                "раздельных очередей полезно проверить, где эти направления могут усиливать друг друга."
            )
            next_action = (
                f"Найдите один результат, который продвинет и «{primary}», и «{secondary}», "
                "затем определите самый маленький первый шаг."
            )
        else:
            title = f"Balance {primary} with {secondary}"
            why_now = (
                f"{primary} leads your profile, while {secondary} is also explicitly "
                f"important at {secondary_weight}/10; this mission tests a useful "
                "overlap instead of treating them as separate queues."
            )
            next_action = (
                f"Find one outcome that advances both {primary} and {secondary}, "
                "then define the smallest first step."
            )
        specs.append(
            (
                title,
                why_now,
                next_action,
                (primary, secondary),
                max(6, weight - 1),
                max(4, secondary_weight),
                8,
                6,
                5,
                safe_risk,
            )
        )
    else:
        if russian:
            title = f"Создать устойчивый ритм для цели «{primary}»"
            why_now = (
                f"«{primary}» — ваш главный приоритет. Небольшой регулярный цикл помогает не зависеть "
                "от разовых всплесков мотивации."
            )
            next_action = (
                f"Определите еженедельный сигнал прогресса по «{primary}», его целевое значение "
                "и дату следующей проверки."
            )
        else:
            title = f"Build a repeatable loop for {primary}"
            why_now = (
                f"{primary} is your dominant explicit priority; a lightweight review "
                "loop prevents progress from depending on one-off motivation."
            )
            next_action = f"Define a weekly signal for {primary}, its target, and the next review point."
        specs.append(
            (
                title,
                why_now,
                next_action,
                (primary,),
                max(6, weight - 1),
                5,
                8,
                6,
                4,
                safe_risk,
            )
        )

    missions: list[Mission] = []
    for index, spec in enumerate(specs, start=1):
        title, why_now, next_action, tags, impact, urgency, leverage, momentum, effort, risk = spec
        mission = Mission(
            id=_mission_id(profile.id, title, index),
            title=title,
            why_now=why_now,
            next_action=next_action,
            impact=min(10, impact),
            urgency=min(10, urgency),
            leverage=min(10, leverage),
            momentum=min(10, momentum),
            effort=min(10, effort),
            risk=min(10, risk),
            status="active",
            tags=tags,
        )
        mission.validate()
        missions.append(mission)
    return missions


def starter_work_sessions(
    profile: Profile,
    missions: list[Mission],
    *,
    locale: str = "en",
) -> list[WorkSessionTemplate]:
    locale = normalize_locale(locale)
    russian = is_russian(locale)
    constraints = (
        ", ".join(profile.constraints[:2])
        if profile.constraints
        else ("текущие ограничения" if russian else "your current constraints")
    )
    sessions: list[WorkSessionTemplate] = []
    for mission in missions:
        if russian:
            steps = (
                f"Переформулируйте цель «{mission.title}» как один измеримый результат.",
                f"Запишите текущие факты, предположения и главное ограничение ({constraints}).",
                (
                    "Выберите самое маленькое действие, которое проверит главную неопределённость: "
                    f"{mission.next_action}"
                ),
                "Проведите один фокус-блок на этом действии и не расширяйте задачу по ходу работы.",
                "Запишите, что изменилось, что вы узнали и какое одно действие лучше сделать следующим.",
            )
            definition = (
                f"По задаче «{mission.title}» зафиксирован конкретный результат, подтверждение "
                "и одно следующее решение."
            )
        else:
            steps = (
                f"Rewrite the target for '{mission.title}' as one measurable outcome.",
                (
                    "List the current evidence, assumptions, and the most relevant "
                    f"constraint ({constraints})."
                ),
                (
                    "Choose the smallest action that tests the biggest uncertainty: "
                    f"{mission.next_action}"
                ),
                (
                    "Spend one focused block completing that action; do not expand scope "
                    "during the block."
                ),
                "Record what changed, what you learned, and the single best next action.",
            )
            definition = (
                f"A concrete result for '{mission.title}' is recorded together with "
                "evidence and one next decision."
            )
        template = WorkSessionTemplate(
            mission_id=mission.id,
            focus_minutes=60,
            steps=steps,
            definition_of_done=definition,
        )
        template.validate()
        sessions.append(template)
    return sessions


def initialize_workspace(
    workspace: UserWorkspace,
    profile: Profile,
    *,
    replace: bool = False,
    locale: str = "en",
) -> tuple[list[Mission], list[WorkSessionTemplate]]:
    if workspace.initialized() and not replace:
        raise ValueError(
            f"user workspace '{workspace.user_id}' already exists; pass --replace to "
            "rebuild it explicitly"
        )
    if profile.id != workspace.user_id:
        raise ValueError("profile id must match workspace user id")

    locale = normalize_locale(locale)
    missions = starter_missions(profile, locale=locale)
    sessions = starter_work_sessions(profile, missions, locale=locale)
    workspace.ensure()

    session_payload = [
        {
            "mission_id": item.mission_id,
            "focus_minutes": item.focus_minutes,
            "steps": list(item.steps),
            "definition_of_done": item.definition_of_done,
        }
        for item in sessions
    ]

    write_json_atomic(workspace.profile_path, profile_payload(profile))
    save_missions(workspace.missions_path, missions)
    write_json_atomic(workspace.work_sessions_path, session_payload)
    if replace and workspace.work_progress_path.exists():
        workspace.work_progress_path.unlink()
    return missions, sessions
