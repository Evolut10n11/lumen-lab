from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .models import Experiment

MARKER_PREFIX = "<!-- lumen-lab:"


@dataclass(frozen=True, slots=True)
class IssueSpec:
    experiment_id: str
    title: str
    body: str

    @property
    def marker(self) -> str:
        return f"{MARKER_PREFIX}{self.experiment_id} -->"


@dataclass(frozen=True, slots=True)
class RemoteIssue:
    number: int
    title: str
    body: str

    def managed_experiment_id(self) -> str | None:
        start = self.body.find(MARKER_PREFIX)
        if start < 0:
            return None
        start += len(MARKER_PREFIX)
        end = self.body.find(" -->", start)
        if end < 0:
            return None
        value = self.body[start:end].strip()
        return value or None


@dataclass(frozen=True, slots=True)
class SyncAction:
    kind: str
    experiment_id: str
    issue_number: int | None
    title: str
    body: str


def issue_spec(experiment: Experiment) -> IssueSpec:
    title = f"[lumen:{experiment.id}] {experiment.title}"
    body = (
        f"{MARKER_PREFIX}{experiment.id} -->\n"
        "Generated from `state/backlog.json` by Lumen Lab.\n\n"
        f"## Hypothesis\n\n{experiment.hypothesis}\n\n"
        "## Planner snapshot\n\n"
        f"- priority score: `{experiment.score():.2f}`\n"
        f"- impact: `{experiment.impact}`\n"
        f"- learning: `{experiment.learning}`\n"
        f"- feasibility: `{experiment.feasibility}`\n"
        f"- novelty: `{experiment.novelty}`\n"
        f"- risk: `{experiment.risk}`\n"
        f"- state: `{experiment.status}`\n\n"
        "This issue is managed by Lumen Lab. Human comments are preserved."
    )
    return IssueSpec(experiment.id, title, body)


def desired_issues(experiments: list[Experiment]) -> list[IssueSpec]:
    return [issue_spec(item) for item in experiments if item.status in {"backlog", "active"}]


def plan_sync(
    experiments: list[Experiment],
    remote_issues: list[RemoteIssue],
) -> list[SyncAction]:
    managed: dict[str, RemoteIssue] = {}
    for issue in remote_issues:
        experiment_id = issue.managed_experiment_id()
        if experiment_id is not None and experiment_id not in managed:
            managed[experiment_id] = issue

    actions: list[SyncAction] = []
    for spec in desired_issues(experiments):
        existing = managed.get(spec.experiment_id)
        if existing is None:
            actions.append(
                SyncAction("create", spec.experiment_id, None, spec.title, spec.body)
            )
            continue
        if existing.title != spec.title or existing.body != spec.body:
            actions.append(
                SyncAction(
                    "update",
                    spec.experiment_id,
                    existing.number,
                    spec.title,
                    spec.body,
                )
            )
    return actions


class GitHubIssueClient:
    def __init__(self, repository: str, token: str) -> None:
        if repository.count("/") != 1:
            raise ValueError("repository must use owner/name form")
        if not token.strip():
            raise ValueError("token is required")
        owner, name = repository.split("/", 1)
        if not owner or not name:
            raise ValueError("repository must use owner/name form")
        self.repository = repository
        self.token = token
        self.base_url = f"https://api.github.com/repos/{repository}"

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "lumen-lab",
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))

    def list_open_issues(self) -> list[RemoteIssue]:
        query = urllib.parse.urlencode({"state": "open", "per_page": 100})
        raw = self._request("GET", f"/issues?{query}")
        issues: list[RemoteIssue] = []
        for item in raw:
            if "pull_request" in item:
                continue
            issues.append(
                RemoteIssue(
                    number=int(item["number"]),
                    title=str(item.get("title") or ""),
                    body=str(item.get("body") or ""),
                )
            )
        return issues

    def apply(self, actions: list[SyncAction]) -> None:
        for action in actions:
            payload = {"title": action.title, "body": action.body}
            if action.kind == "create":
                self._request("POST", "/issues", payload)
            elif action.kind == "update" and action.issue_number is not None:
                self._request("PATCH", f"/issues/{action.issue_number}", payload)
            else:
                raise ValueError(f"unsupported sync action: {action.kind}")
