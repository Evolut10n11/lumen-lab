from __future__ import annotations

from lumen_lab.llm_planner import OpenAICompatiblePlanner, recommend_with_fallback
from lumen_lab.models import Experiment


def _experiments() -> list[Experiment]:
    return [
        Experiment(
            id="exp-a",
            title="Safer",
            hypothesis="A",
            impact=7,
            learning=7,
            feasibility=9,
            novelty=5,
            risk=1,
        ),
        Experiment(
            id="exp-b",
            title="Bolder",
            hypothesis="B",
            impact=10,
            learning=10,
            feasibility=5,
            novelty=9,
            risk=6,
        ),
    ]


def test_valid_llm_recommendation_is_used() -> None:
    def transport(endpoint, payload, headers, timeout):
        assert endpoint == "http://localhost:11434/v1/chat/completions"
        assert payload["model"] == "local-model"
        assert "Authorization" not in headers
        assert timeout == 2.0
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"experiment_id":"exp-b","reason":"Higher learning value"}'
                    }
                }
            ]
        }

    adapter = OpenAICompatiblePlanner(
        endpoint="http://localhost:11434/v1/chat/completions",
        model="local-model",
        timeout=2.0,
        transport=transport,
    )
    recommendation = recommend_with_fallback(_experiments(), adapter)

    assert recommendation.experiment is not None
    assert recommendation.experiment.id == "exp-b"
    assert recommendation.source == "llm"
    assert recommendation.reason == "Higher learning value"


def test_unknown_id_falls_back_to_deterministic_planner() -> None:
    def transport(endpoint, payload, headers, timeout):
        return {
            "choices": [
                {"message": {"content": '{"experiment_id":"invented","reason":"Nope"}'}}
            ]
        }

    adapter = OpenAICompatiblePlanner("http://local", "model", transport=transport)
    recommendation = recommend_with_fallback(_experiments(), adapter)

    assert recommendation.experiment is not None
    assert recommendation.experiment.id == "exp-b"
    assert recommendation.source == "deterministic-fallback"
    assert "outside the current backlog" in recommendation.reason


def test_transport_failure_falls_back_without_raising() -> None:
    def transport(endpoint, payload, headers, timeout):
        raise OSError("offline")

    adapter = OpenAICompatiblePlanner("http://local", "model", transport=transport)
    recommendation = recommend_with_fallback(_experiments(), adapter)

    assert recommendation.experiment is not None
    assert recommendation.experiment.id == "exp-b"
    assert recommendation.source == "deterministic-fallback"
    assert "failed safely" in recommendation.reason


def test_no_adapter_uses_deterministic_planner() -> None:
    recommendation = recommend_with_fallback(_experiments())

    assert recommendation.experiment is not None
    assert recommendation.experiment.id == "exp-b"
    assert recommendation.source == "deterministic"


def test_markdown_fenced_json_is_supported() -> None:
    def transport(endpoint, payload, headers, timeout):
        return {
            "choices": [
                {
                    "message": {
                        "content": "```json\n{\"experiment_id\":\"exp-a\",\"reason\":\"Lower risk\"}\n```"
                    }
                }
            ]
        }

    adapter = OpenAICompatiblePlanner("http://local", "model", transport=transport)
    recommendation = recommend_with_fallback(_experiments(), adapter)

    assert recommendation.experiment is not None
    assert recommendation.experiment.id == "exp-a"
    assert recommendation.source == "llm"
