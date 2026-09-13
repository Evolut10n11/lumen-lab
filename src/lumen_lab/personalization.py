from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

from .mission_radar import Mission
from .profile import CandidateGenerationPolicy, Profile, normalized_label
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


def starter_missions(profile: Profile) -> list[Mission]:
    """Create a small portfolio solely from the explicit user's profile."""
    if not profile.priorities:
        raise ValueError("at least one priority is required to create personalized missions")

    ordered_priorities = sorted(
        profile.priorities.items(),
        key=lambda item: (-item[1], normalized_label(item[0])),
    )
    primary, weight = ordered_priorities[0]
    interest = profile.interests[0] if profile.interests else None
    skill = profile.skills[0] if profile.skills else None
    safe_risk = max(1, min(profile.risk_tolerance, 4))

    specs: list[tuple[str, str, str, tuple[str, ...], int, int, int, int, int, int]] = [
        (
            f"Move {primary} forward",
            f"You ranked {primary} at {weight}/10, so it should receive a concrete outcome before lower-priority work.",
            f"Define one measurable result for {primary} that can be completed or validated within seven days.",
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
        specs.append(
            (
                f"Connect {interest} to {primary}",
                f"{interest} is an explicit interest and {primary} is your highest-weighted priority; connecting them can create motivation and useful evidence at the same time.",
                f"Choose one small {interest} experiment that produces evidence for {primary}.",
                (primary, interest) if normalized_label(primary) != normalized_label(interest) else (primary,),
                max(6, weight - 1),
                max(5, weight - 1),
                7,
                7,
                5,
                safe_risk,
            )
        )
    else:
        specs.append(
            (
                f"Create visible evidence for {primary}",
                f"Your profile makes {primary} the current leading priority, but progress becomes more useful when it leaves a concrete artifact or measurable result.",
                f"Pick the smallest visible artifact that would prove progress on {primary} and define its acceptance criteria.",
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
        specs.append(
            (
                f"Use {skill} to accelerate {primary}",
                f"{skill} is already in your skill set, so using it against {primary} should reduce ramp-up cost and turn existing capability into leverage.",
                f"Identify one task for {primary} where {skill} removes the most uncertainty, then complete the first bounded slice.",
                (primary, skill) if normalized_label(primary) != normalized_label(skill) else (primary,),
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
        specs.append(
            (
                f"Balance {primary} with {secondary}",
                f"{primary} leads your profile, while {secondary} is also explicitly important at {secondary_weight}/10; this mission tests a useful overlap instead of treating them as separate queues.",
                f"Find one outcome that advances both {primary} and {secondary}, then define the smallest first step.",
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
        specs.append(
            (
                f"Build a repeatable loop for {primary}",
                f"{primary} is your dominant explicit priority; a lightweight review loop prevents progress from depending on one-off motivation.",
                f"Define a weekly signal for {primary}, its target, and the next review point.",
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
) -> list[WorkSessionTemplate]:
    constraints = ", ".join(profile.constraints[:2]) if profile.constraints else "your current constraints"
    sessions: list[WorkSessionTemplate] = []
    for mission in missions:
        template = WorkSessionTemplate(
            mission_id=mission.id,
            focus_minutes=60,
            steps=(
                f"Rewrite the target for '{mission.title}' as one measurable outcome.",
                f"List the current evidence, assumptions, and the most relevant constraint ({constraints}).",
                f"Choose the smallest action that tests the biggest uncertainty: {mission.next_action}",
                "Spend one focused block completing that action; do not expand scope during the block.",
                "Record what changed, what you learned, and the single best next action.",
            ),
            definition_of_done=(
                f"A concrete result for '{mission.title}' is recorded together with evidence and one next decision."
            ),
        )
        template.validate()
        sessions.append(template)
    return sessions


def initialize_workspace(
    workspace: UserWorkspace,
    profile: Profile,
    *,
    replace: bool = False,
) -> tuple[list[Mission], list[WorkSessionTemplate]]:
    if workspace.initialized() and not replace:
        raise ValueError(
            f"user workspace '{workspace.user_id}' already exists; pass --replace to rebuild it explicitly"
        )
    if profile.id != workspace.user_id:
        raise ValueError("profile id must match workspace user id")

    missions = starter_missions(profile)
    sessions = starter_work_sessions(profile, missions)
    workspace.ensure()

    mission_payload: list[dict[str, object]] = []
    for mission in missions:
        item = mission.to_dict()
        item.pop("score")
        mission_payload.append(item)

    session_payload = [
        {
            "mission_id": item.mission_id,
            "focus_minutes": item.focus_minutes,
            "steps": list(item.steps),
            "definition_of_done": item.definition_of_done,
        }
        for item in sessions
    ]

    workspace.profile_path.write_text(
        json.dumps(profile_payload(profile), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    workspace.missions_path.write_text(
        json.dumps(mission_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    workspace.work_sessions_path.write_text(
        json.dumps(session_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if replace and workspace.work_progress_path.exists():
        workspace.work_progress_path.unlink()
    return missions, sessions
