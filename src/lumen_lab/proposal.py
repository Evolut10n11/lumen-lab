from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.request import Request, urlopen

from .mission_radar import Mission, ranked_missions
from .models import Experiment
from .profile import Profile, normalized_label

PROPOSAL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
MODEL_FIELDS = {
    "id",
    "title",
    "hypothesis",
    "tags",
    "impact",
    "learning",
    "feasibility",
    "novelty",
    "risk",
    "rationale",
    "evidence",
}
Transport = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


def _labels(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"proposal {name} must be a non-empty JSON list")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"proposal {name} must contain non-empty strings")
        cleaned = item.strip()
        normalized = normalized_label(cleaned)
        if normalized in seen:
            raise ValueError(f"proposal {name} contains duplicate value: {cleaned}")
        seen.add(normalized)
        result.append(cleaned)
    return tuple(result)


def normalized_title(value: str) -> str:
    return " ".join(value.casefold().split())


def slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return text[:48] or "candidate"


@dataclass(frozen=True, slots=True)
class Proposal:
    id: str
    title: str
    hypothesis: str
    tags: tuple[str, ...]
    impact: int
    learning: int
    feasibility: int
    novelty: int
    risk: int
    rationale: str
    evidence: tuple[str, ...]
    source: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Proposal:
        expected = MODEL_FIELDS | {"source"}
        unknown = set(raw) - expected
        missing = expected - set(raw)
        if unknown:
            raise ValueError(f"unknown proposal fields: {', '.join(sorted(unknown))}")
        if missing:
            raise ValueError(f"missing proposal fields: {', '.join(sorted(missing))}")
        proposal = cls(
            id=raw["id"],
            title=raw["title"],
            hypothesis=raw["hypothesis"],
            tags=_labels(raw["tags"], "tags"),
            impact=raw["impact"],
            learning=raw["learning"],
            feasibility=raw["feasibility"],
            novelty=raw["novelty"],
            risk=raw["risk"],
            rationale=raw["rationale"],
            evidence=_labels(raw["evidence"], "evidence"),
            source=raw["source"],
        )
        proposal.validate()
        return proposal

    def validate(self) -> None:
        if not isinstance(self.id, str) or not PROPOSAL_ID_RE.fullmatch(self.id):
            raise ValueError("proposal id must be a safe lowercase identifier")
        for name in ("title", "hypothesis", "rationale"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"proposal {name} must be a non-empty string")
        for name in ("impact", "learning", "feasibility", "novelty", "risk"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 10:
                raise ValueError(f"proposal {name} must be an integer from 1 to 10")
        if self.source not in {"deterministic", "llm"}:
            raise ValueError("proposal source must be deterministic or llm")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "hypothesis": self.hypothesis,
            "tags": list(self.tags),
            "impact": self.impact,
            "learning": self.learning,
            "feasibility": self.feasibility,
            "novelty": self.novelty,
            "risk": self.risk,
            "rationale": self.rationale,
            "evidence": list(self.evidence),
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class ProposalBatch:
    proposals: tuple[Proposal, ...]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposals": [item.to_dict() for item in self.proposals],
            "warnings": list(self.warnings),
        }


def evidence_index(
    profile: Profile,
    missions: list[Mission],
    experiments: list[Experiment],
) -> set[str]:
    evidence = {f"profile:{profile.id}"}
    evidence.update(
        f"profile:priority:{normalized_label(name)}" for name in profile.priorities
    )
    evidence.update(f"mission:{mission.id}" for mission in missions)
    evidence.update(f"experiment:{experiment.id}" for experiment in experiments)
    return evidence


def validate_evidence(proposal: Proposal, allowed: set[str]) -> None:
    unknown = sorted(set(proposal.evidence) - allowed)
    if unknown:
        detail = ", ".join(unknown)
        raise ValueError(f"proposal {proposal.id} references unknown evidence: {detail}")


def _existing_titles(experiments: list[Experiment]) -> set[str]:
    return {normalized_title(item.title) for item in experiments}


def deterministic_proposals(
    profile: Profile,
    missions: list[Mission],
    experiments: list[Experiment],
) -> list[Proposal]:
    policy = profile.candidate_generation_policy
    if policy.mode == "disabled":
        return []

    allowed = evidence_index(profile, missions, experiments)
    existing_ids = {item.id for item in experiments}
    seen_titles = _existing_titles(experiments)
    proposals: list[Proposal] = []
    for mission in ranked_missions(missions, profile):
        if mission.risk > profile.risk_tolerance:
            continue
        matched = [
            (tag, weight)
            for tag in mission.tags
            if (weight := profile.priority_for(tag)) is not None
        ]
        matched.sort(key=lambda item: (-item[1], normalized_label(item[0])))
        primary_tag = matched[0][0] if matched else "general"
        proposal_id = f"mission-{slug(mission.id)}"
        title = f"Validate {mission.title}"
        if proposal_id in existing_ids or normalized_title(title) in seen_titles:
            continue
        evidence = [f"profile:{profile.id}", f"mission:{mission.id}"]
        priority_ref = f"profile:priority:{normalized_label(primary_tag)}"
        if priority_ref in allowed:
            evidence.append(priority_ref)
        proposal = Proposal(
            id=proposal_id,
            title=title,
            hypothesis=(
                f"A bounded experiment around '{mission.next_action}' will produce useful "
                f"evidence about progress on {mission.title}."
            ),
            tags=mission.tags or (primary_tag,),
            impact=mission.impact,
            learning=max(6, min(10, mission.leverage)),
            feasibility=max(1, min(10, 11 - mission.effort)),
            novelty=max(5, min(10, mission.momentum)),
            risk=mission.risk,
            rationale=(
                f"Mission '{mission.id}' ranks highly for profile '{profile.id}'; "
                f"primary alignment is '{primary_tag}'."
            ),
            evidence=tuple(evidence),
            source="deterministic",
        )
        validate_evidence(proposal, allowed)
        proposals.append(proposal)
        seen_titles.add(normalized_title(title))
        if len(proposals) >= policy.max_candidates:
            break
    return proposals


class ProposalAdapter(Protocol):
    def generate(
        self,
        profile: Profile,
        missions: list[Mission],
        experiments: list[Experiment],
        allowed_evidence: set[str],
    ) -> list[Proposal]: ...


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
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - explicit CLI endpoint.
        raw = response.read().decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object")
    return data


def _extract_content(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ValueError("LLM response does not contain a valid choice")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ValueError("LLM choice does not contain text content")
    return message["content"].strip()


def _parse_json(content: str) -> dict[str, Any]:
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
        raise ValueError("model proposal response must be a JSON object")
    return parsed


@dataclass(slots=True)
class OpenAICompatibleProposalGenerator:
    endpoint: str
    model: str
    token: str = ""
    timeout: float = 10.0
    transport: Transport = _http_transport

    def generate(
        self,
        profile: Profile,
        missions: list[Mission],
        experiments: list[Experiment],
        allowed_evidence: set[str],
    ) -> list[Proposal]:
        prompt = {
            "profile": {
                "id": profile.id,
                "priorities": profile.priorities,
                "skills": list(profile.skills),
                "interests": list(profile.interests),
                "constraints": list(profile.constraints),
                "preferred_stack": list(profile.preferred_stack),
                "risk_tolerance": profile.risk_tolerance,
            },
            "missions": [mission.to_dict() for mission in missions if mission.status == "active"],
            "existing_experiments": [
                {"id": item.id, "title": item.title, "status": item.status}
                for item in experiments
            ],
            "allowed_evidence": sorted(allowed_evidence),
        }
        instructions = (
            "Propose bounded software experiments. Return only JSON with key 'proposals' whose "
            "value is an array. Each item must contain exactly these keys: "
            f"{', '.join(sorted(MODEL_FIELDS))}. Use only allowed evidence references, never "
            "invent existing IDs, and keep risk within the supplied profile risk tolerance."
        )
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a conservative proposal generator with no execution authority."
                    ),
                },
                {"role": "user", "content": f"{instructions}\n\n{json.dumps(prompt)}"},
            ],
            "temperature": 0,
        }
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        response = self.transport(self.endpoint, payload, headers, self.timeout)
        parsed = _parse_json(_extract_content(response))
        raw_items = parsed.get("proposals")
        if not isinstance(raw_items, list):
            raise ValueError("model response proposals must be a JSON list")
        proposals: list[Proposal] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                raise ValueError("model proposal must be a JSON object")
            if set(raw) != MODEL_FIELDS:
                raise ValueError("model proposal fields do not match the proposal schema")
            proposal = Proposal.from_dict({**raw, "source": "llm"})
            validate_evidence(proposal, allowed_evidence)
            if proposal.risk > profile.risk_tolerance:
                raise ValueError(f"proposal {proposal.id} exceeds profile risk tolerance")
            proposals.append(proposal)
        return proposals


def generate_proposals(
    profile: Profile,
    missions: list[Mission],
    experiments: list[Experiment],
    adapter: ProposalAdapter | None = None,
) -> ProposalBatch:
    policy = profile.candidate_generation_policy
    if policy.mode == "disabled":
        return ProposalBatch(())

    deterministic = deterministic_proposals(profile, missions, experiments)
    if policy.mode != "optional-llm" or not policy.allow_llm or adapter is None:
        return ProposalBatch(tuple(deterministic[: policy.max_candidates]))

    allowed = evidence_index(profile, missions, experiments)
    warnings: list[str] = []
    try:
        generated = adapter.generate(profile, missions, experiments, allowed)
    except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        warnings.append(f"LLM proposals failed safely: {type(exc).__name__}.")
        return ProposalBatch(tuple(deterministic[: policy.max_candidates]), tuple(warnings))

    existing_ids = {item.id for item in experiments}
    seen_ids = {item.id for item in deterministic}
    seen_titles = _existing_titles(experiments) | {
        normalized_title(item.title) for item in deterministic
    }
    merged = list(deterministic)
    for proposal in generated:
        if proposal.id in existing_ids or proposal.id in seen_ids:
            continue
        title_key = normalized_title(proposal.title)
        if title_key in seen_titles or proposal.risk > profile.risk_tolerance:
            continue
        validate_evidence(proposal, allowed)
        merged.append(proposal)
        seen_ids.add(proposal.id)
        seen_titles.add(title_key)
        if len(merged) >= policy.max_candidates:
            break
    return ProposalBatch(tuple(merged[: policy.max_candidates]), tuple(warnings))


def load_proposal_batch(text: str) -> ProposalBatch:
    raw = json.loads(text)
    if not isinstance(raw, dict) or set(raw) != {"proposals", "warnings"}:
        raise ValueError("proposal snapshot must contain proposals and warnings")
    items = raw["proposals"]
    warnings = raw["warnings"]
    if not isinstance(items, list) or not isinstance(warnings, list):
        raise ValueError("proposal snapshot fields must be JSON lists")
    if not all(isinstance(item, dict) for item in items):
        raise ValueError("proposal snapshot entries must be JSON objects")
    if not all(isinstance(item, str) for item in warnings):
        raise ValueError("proposal snapshot warnings must be strings")
    return ProposalBatch(tuple(Proposal.from_dict(item) for item in items), tuple(warnings))


def accept_proposal(
    proposal: Proposal,
    experiment_id: str,
    profile: Profile,
    missions: list[Mission],
    experiments: list[Experiment],
) -> Experiment:
    proposal.validate()
    validate_evidence(proposal, evidence_index(profile, missions, experiments))
    if proposal.risk > profile.risk_tolerance:
        raise ValueError(f"proposal {proposal.id} exceeds profile risk tolerance")
    if any(item.id == experiment_id for item in experiments):
        raise ValueError(f"experiment id already exists: {experiment_id}")
    if normalized_title(proposal.title) in _existing_titles(experiments):
        raise ValueError(f"experiment title already exists: {proposal.title}")
    experiment = Experiment(
        id=experiment_id,
        title=proposal.title,
        hypothesis=proposal.hypothesis,
        impact=proposal.impact,
        learning=proposal.learning,
        feasibility=proposal.feasibility,
        novelty=proposal.novelty,
        risk=proposal.risk,
        status="backlog",
    )
    experiment.validate()
    return experiment
