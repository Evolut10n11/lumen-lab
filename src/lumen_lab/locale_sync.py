from __future__ import annotations

from dataclasses import replace

from .localization import normalize_locale
from .mission_radar import load_missions, save_missions
from .onboarding import load_onboarding_context, save_onboarding_context
from .personalization import starter_missions, starter_work_sessions
from .profile import load_profile
from .state_io import write_json_atomic
from .work_session import WorkSessionTemplate, load_templates
from .workspace import UserWorkspace

_PERSONAL_MISSION_PREFIX = "personal-"


def _session_payload(templates: list[WorkSessionTemplate]) -> list[dict[str, object]]:
    return [
        {
            "mission_id": template.mission_id,
            "focus_minutes": template.focus_minutes,
            "steps": list(template.steps),
            "definition_of_done": template.definition_of_done,
        }
        for template in templates
    ]


def synchronize_workspace_locale(workspace: UserWorkspace, locale: str) -> bool:
    """Re-localize generated starter work while preserving user-owned progress and IDs.

    Conversational onboarding stores the last explicit locale in onboarding context.  If a
    later desktop request asks for another locale, only the deterministic starter missions
    and their work-session copy are regenerated.  Stable mission IDs, status, focus windows,
    progress files, feedback, and unrelated/GitHub-derived missions are left untouched.
    """

    locale = normalize_locale(locale)
    context = load_onboarding_context(workspace.onboarding_context_path)
    if context is None:
        return False

    stored_locale = normalize_locale(str(context.get("locale", "en")))
    if stored_locale == locale:
        return False

    profile = load_profile(workspace.profile_path)
    missions = load_missions(workspace.missions_path)
    templates = load_templates(workspace.work_sessions_path)

    existing_starters = [
        mission for mission in missions if mission.id.startswith(_PERSONAL_MISSION_PREFIX)
    ]
    if existing_starters:
        generated = starter_missions(profile, locale=locale)
        if len(generated) != len(existing_starters):
            raise ValueError(
                "cannot re-localize starter missions because the generated portfolio shape changed"
            )

        localized_starters = [
            replace(generated_item, id=current.id, status=current.status)
            for current, generated_item in zip(existing_starters, generated, strict=True)
        ]
        localized_by_id = {mission.id: mission for mission in localized_starters}
        updated_missions = [localized_by_id.get(mission.id, mission) for mission in missions]

        generated_templates = starter_work_sessions(
            profile,
            localized_starters,
            locale=locale,
        )
        current_templates = {template.mission_id: template for template in templates}
        localized_templates: dict[str, WorkSessionTemplate] = {}
        for generated_template in generated_templates:
            current = current_templates.get(generated_template.mission_id)
            if current is None:
                raise ValueError(
                    "cannot re-localize starter work because a work-session template is missing"
                )
            localized_templates[generated_template.mission_id] = replace(
                generated_template,
                focus_minutes=current.focus_minutes,
            )
        updated_templates = [
            localized_templates.get(template.mission_id, template) for template in templates
        ]

        save_missions(workspace.missions_path, updated_missions)
        write_json_atomic(workspace.work_sessions_path, _session_payload(updated_templates))

    context["locale"] = locale
    save_onboarding_context(workspace.onboarding_context_path, context)
    return True
