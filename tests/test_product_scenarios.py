from __future__ import annotations

from pathlib import Path

import pytest

from lumen_lab.desktop_bridge import dispatch


def _request(
    action: str,
    *,
    user_id: str = "default",
    locale: str = "ru",
    **payload: object,
):
    return dispatch(
        {
            "action": action,
            "user_id": user_id,
            "locale": locale,
            "payload": payload,
        }
    )


@pytest.mark.parametrize(
    ("current_context", "desired_change", "friction", "focus_minutes", "theme"),
    [
        (
            "Работаю backend-разработчиком и готовлюсь к собеседованиям",
            "Хочу получить более сильную AI-роль",
            "После работы мало энергии",
            30,
            "карьерная подготовка и доказательства навыков",
        ),
        (
            "Учусь в университете, впереди сессия и диплом",
            "Хочу закрыть сессию без долгов и продвинуть диплом",
            "Откладываю сложные задачи",
            15,
            "ближайший учебный дедлайн",
        ),
        (
            "Делаю свой pet project и хочу довести его до пользователей",
            "Хочу запустить первую полезную версию продукта",
            "Постоянно расширяю scope",
            60,
            "один пользовательский результат в текущем проекте",
        ),
        (
            "После работы рисую и хочу начать публиковать иллюстрации",
            "Хочу регулярно публиковать работы и получать отзывы",
            "Перфекционизм мешает выкладывать",
            30,
            "публикация одной законченной творческой работы",
        ),
        (
            "Много работаю дома, сбился режим и почти не двигаюсь",
            "Хочу чувствовать себя бодрее и вернуть нормальный режим",
            "Нерегулярный график",
            15,
            "небольшой устойчивый эксперимент с режимом",
        ),
    ],
)
def test_first_run_produces_distinct_actionable_scenarios(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    current_context: str,
    desired_change: str,
    friction: str,
    focus_minutes: int,
    theme: str,
) -> None:
    monkeypatch.chdir(tmp_path)

    dashboard = _request(
        "guided_onboard",
        display_name="Тест",
        current_context=current_context,
        desired_change=desired_change,
        friction=friction,
        focus_minutes=focus_minutes,
    )

    assert dashboard["today"]["focus_minutes"] == focus_minutes
    assert dashboard["user"]["interests"] == [theme]

    titles = [mission["title"] for mission in dashboard["radar"]]
    assert any(theme in title for title in titles)
    assert all(current_context not in title for title in titles)
    assert dashboard["today"]["why_now"]
    assert dashboard["today"]["definition_of_done"]
    assert len(dashboard["today"]["steps"]) >= 3


def test_vague_answer_creates_a_clarification_task_not_false_specificity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    dashboard = _request(
        "guided_onboard",
        display_name="Олег",
        current_context="Всё навалилось, работа и бытовые дела",
        desired_change="Хочу чтобы стало лучше",
        friction="Не знаю с чего начать",
        focus_minutes=30,
    )

    assert dashboard["user"]["priorities"] == {
        "Уточнить, что именно должно измениться": 10
    }
    assert "Уточнить" in dashboard["today"]["title"]


def test_repeated_deferral_causes_lumen_to_ask_for_smaller_or_better_timed_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    dashboard = _request(
        "guided_onboard",
        display_name="Аня",
        current_context="Учусь в университете и готовлюсь к экзаменам",
        desired_change="Хочу закрыть сессию без долгов",
        friction="После пар мало сил",
        focus_minutes=30,
    )

    for _ in range(3):
        dashboard = _request(
            "react",
            reaction="not_now",
            mission_id=dashboard["today"]["mission_id"],
        )

    clarification = dashboard["clarification"]
    assert clarification is not None
    assert clarification["id"] == "repeated_deferral"
    assert {item["choice"] for item in clarification["options"]} == {
        "make_smaller",
        "bad_timing",
        "not_useful",
    }


def test_repeated_rejection_makes_lumen_question_its_goal_assumption(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    dashboard = _request(
        "guided_onboard",
        display_name="Иван",
        current_context="Готовлюсь к собеседованиям на AI-роли",
        desired_change="Хочу получить сильную AI-роль",
        friction="Много параллельных задач",
        focus_minutes=30,
    )

    for _ in range(2):
        dashboard = _request(
            "react",
            reaction="less_like_this",
            mission_id=dashboard["today"]["mission_id"],
        )

    clarification = dashboard["clarification"]
    assert clarification is not None
    assert clarification["id"] == "primary_goal_fit"
    assert "всё ещё направление" in clarification["prompt"]


def test_release_journey_survives_deferral_completion_revision_and_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    dashboard = _request(
        "guided_onboard",
        display_name="Аня",
        current_context="Развиваю свой продукт после основной работы",
        desired_change="Хочу довести полезный сценарий до пользователей",
        friction="Легко распыляюсь",
        focus_minutes=30,
    )
    mission_id = dashboard["today"]["mission_id"]
    step_count = dashboard["today"]["progress"]["total"]

    dashboard = _request("select_companion", character_id="kiro")
    assert dashboard["companion"]["selected"]["id"] == "kiro"

    dashboard = _request("react", reaction="not_now", mission_id=mission_id)
    assert mission_id in {mission["id"] for mission in dashboard["paused"]}
    dashboard = _request("resume_mission", mission_id=mission_id)
    assert mission_id not in {mission["id"] for mission in dashboard["paused"]}

    for step in range(1, step_count + 1):
        dashboard = _request("complete_step", mission_id=mission_id, step=step)
    earned_xp = step_count * 5 + 25
    assert dashboard["companion"]["total_xp"] == earned_xp
    assert dashboard["summary"]["completed_missions"] == 1

    dashboard = _request(
        "revise_direction",
        desired_change="Хочу подготовить понятный запуск для первых пользователей",
        current_context="Первый сценарий уже проверен",
        friction="Нужно удержать узкий объём",
        focus_minutes=15,
    )
    assert dashboard["companion"]["selected"]["id"] == "kiro"
    assert dashboard["companion"]["total_xp"] == earned_xp
    assert dashboard["today"]["focus_minutes"] == 15

    revised_mission_id = dashboard["today"]["mission_id"]
    dashboard = _request(
        "complete_step",
        mission_id=revised_mission_id,
        step=1,
    )
    assert dashboard["companion"]["total_xp"] == earned_xp + 5

    restarted = _request("bootstrap")
    assert restarted["initialized"] is True
    assert restarted["dashboard"]["companion"]["selected"]["id"] == "kiro"
    assert restarted["dashboard"]["companion"]["total_xp"] == earned_xp + 5
