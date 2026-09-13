from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.request import Request, urlopen

from .models import Experiment
from .planner import choose_next


@dataclass(frozen=True, slots=True)
class Recommendation:
    experiment: Experiment | None
    source: str
    reason: str


class PlannerAdapter(Protocol):
    def recommend(self, experiments: list[Experiment]) -> tuple[str, str] | None: ...


Transport = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


def _http_transport(
    endpoint: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    request = Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - endpoint is explicit CLI input.
        raw = response.read().decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object")
    return data


@dataclass(slots=True)
class OpenAICompatiblePlanner:
    endpoint: str
    model: str
    token: str = ""
    timeout: float = 10.0
    transport: Transport = _http_transport

    def recommend(self, experiments: list[Experiment]) -> tuple[str, str] | None:
        candidates = [item for item in experiments if item.status == "backlog"]
        if not candidates:
            return None

        candidate_text = "\n".join(
            (
                f"- {item.id}: {item.title}; score={item.score():.2f}; "
                f"risk={item.risk}; hypothesis={item.hypothesis}"
            )
            for item in candidates
        )
        prompt = (
            "Choose exactly one experiment from the supplied backlog. Prefer high learning and "
            "impact, but account for feasibility and risk. Return only a JSON object with keys "
            '"experiment_id" and "reason". Do not invent IDs.\n\nBacklog:\n'
            f"{candidate_text}"
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a conservative software R&D planning assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = self.transport(self.endpoint, payload, headers, self.timeout)
        content = _extract_content(response)
        parsed = _parse_model_json(content)
        experiment_id = parsed.get("experiment_id")
        reason = parsed.get("reason")
        if not isinstance(experiment_id, str) or not isinstance(reason, str):
            return None
        return experiment_id.strip(), reason.strip()


def _extract_content(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("LLM response does not contain choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("LLM choice must be an object")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ValueError("LLM choice does not contain a message")
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("LLM message content must be text")
    return content.strip()


def _parse_model_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            lines = lines[1:-1]
            if lines and lines[0].strip().lower() == "json":
                lines = lines[1:]
            text = "\n".join(lines).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("model recommendation must be a JSON object")
    return parsed


def recommend_with_fallback(
    experiments: Iterable[Experiment],
    adapter: PlannerAdapter | None = None,
) -> Recommendation:
    items = list(experiments)
    deterministic = choose_next(items)
    if adapter is None:
        return Recommendation(
            experiment=deterministic,
            source="deterministic",
            reason="No LLM endpoint configured; using deterministic planner.",
        )

    try:
        suggestion = adapter.recommend(items)
    except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return Recommendation(
            experiment=deterministic,
            source="deterministic-fallback",
            reason=f"LLM planner failed safely: {type(exc).__name__}.",
        )

    if suggestion is None:
        return Recommendation(
            experiment=deterministic,
            source="deterministic-fallback",
            reason="LLM planner returned no valid recommendation.",
        )

    experiment_id, reason = suggestion
    candidate = next(
        (item for item in items if item.id == experiment_id and item.status == "backlog"),
        None,
    )
    if candidate is None:
        return Recommendation(
            experiment=deterministic,
            source="deterministic-fallback",
            reason="LLM planner suggested an ID outside the current backlog.",
        )

    return Recommendation(experiment=candidate, source="llm", reason=reason)
