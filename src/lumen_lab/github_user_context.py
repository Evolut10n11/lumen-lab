from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GITHUB_CONTEXT_SCHEMA_VERSION = 1
_GITHUB_USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


def validate_github_username(value: str) -> str:
    username = value.strip()
    if not username:
        raise ValueError("GitHub username must be a non-empty string")
    if not _GITHUB_USERNAME_RE.fullmatch(username):
        raise ValueError(
            "GitHub username must use letters, numbers or hyphens, and cannot start or end "
            "with a hyphen"
        )
    return username


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def _timestamp(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _repo_payload(raw: dict[str, Any], event_count: int = 0) -> dict[str, Any]:
    topics_raw = raw.get("topics")
    topics = [
        item.strip()
        for item in topics_raw
        if isinstance(item, str) and item.strip()
    ] if isinstance(topics_raw, list) else []
    owner_raw = raw.get("owner")
    owner = owner_raw.get("login") if isinstance(owner_raw, dict) else None
    return {
        "name": str(raw.get("name") or ""),
        "full_name": str(raw.get("full_name") or ""),
        "owner": str(owner or ""),
        "description": _text(raw.get("description")),
        "language": _text(raw.get("language")),
        "topics": sorted(set(topics), key=str.casefold),
        "fork": bool(raw.get("fork", False)),
        "archived": bool(raw.get("archived", False)),
        "stars": int(raw.get("stargazers_count") or 0),
        "pushed_at": _timestamp(raw.get("pushed_at")),
        "updated_at": _timestamp(raw.get("updated_at")),
        "event_count": event_count,
    }


def _event_repo_counts(events: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for event in events:
        repo = event.get("repo")
        if not isinstance(repo, dict):
            continue
        name = _text(repo.get("name"))
        if name:
            counts[name] += 1
    return counts


def build_github_snapshot(
    profile: dict[str, Any],
    repositories: list[dict[str, Any]],
    events: list[dict[str, Any]],
    *,
    fetched_at: str | None = None,
) -> dict[str, Any]:
    """Normalize public GitHub API responses into user-scoped product evidence."""
    username = validate_github_username(str(profile.get("login") or ""))
    event_counts = _event_repo_counts(events)

    repos = [
        _repo_payload(raw, event_count=event_counts.get(str(raw.get("full_name") or ""), 0))
        for raw in repositories
        if isinstance(raw, dict) and raw.get("full_name")
    ]
    repos.sort(
        key=lambda item: (
            item["pushed_at"] or "",
            item["event_count"],
            item["full_name"].casefold(),
        ),
        reverse=True,
    )

    repo_names = {item["full_name"] for item in repos}
    activity_only = [
        {"full_name": name, "event_count": count}
        for name, count in event_counts.most_common(8)
        if name not in repo_names
    ]

    languages: Counter[str] = Counter()
    topics: Counter[str] = Counter()
    for repo in repos:
        if repo["archived"]:
            continue
        language = repo.get("language")
        if isinstance(language, str) and language:
            languages[language] += 1
        topics.update(repo.get("topics", []))

    active = [repo for repo in repos if not repo["archived"]][:5]
    top_language = languages.most_common(1)[0][0] if languages else None
    top_project = active[0]["full_name"] if active else None

    return {
        "schema_version": GITHUB_CONTEXT_SCHEMA_VERSION,
        "source": "github_public",
        "fetched_at": fetched_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "account": {
            "username": username,
            "name": _text(profile.get("name")),
            "bio": _text(profile.get("bio")),
            "company": _text(profile.get("company")),
            "location": _text(profile.get("location")),
            "public_repos": int(profile.get("public_repos") or 0),
            "followers": int(profile.get("followers") or 0),
        },
        "active_repositories": active,
        "activity_only_repositories": activity_only,
        "languages": [
            {"name": name, "repository_count": count}
            for name, count in languages.most_common(6)
        ],
        "topics": [
            {"name": name, "repository_count": count}
            for name, count in topics.most_common(8)
        ],
        "signals": {
            "active_project": top_project,
            "primary_language": top_language,
            "active_repository_count": len(active),
            "public_event_repository_count": len(event_counts),
        },
    }


class GitHubPublicContextClient:
    """Read-only GitHub client for opt-in public profile context."""

    def __init__(self, *, timeout: int = 15) -> None:
        self.timeout = timeout
        self.base_url = "https://api.github.com"

    def _request(self, path: str, params: dict[str, str | int] | None = None) -> Any:
        query = "" if not params else "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(
            f"{self.base_url}{path}{query}",
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "lumen-desktop",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise ValueError("GitHub profile was not found") from exc
            if exc.code in {403, 429}:
                raise ValueError(
                    "GitHub public API limit was reached. Try again later or connect with "
                    "authenticated access when that option is available."
                ) from exc
            raise ValueError(f"GitHub returned HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise ValueError("Could not reach GitHub. Check your internet connection.") from exc

    def fetch(self, username: str) -> dict[str, Any]:
        username = validate_github_username(username)
        profile = self._request(f"/users/{username}")
        repositories = self._request(
            f"/users/{username}/repos",
            {"per_page": 100, "sort": "pushed", "direction": "desc", "type": "owner"},
        )
        events = self._request(
            f"/users/{username}/events/public",
            {"per_page": 100},
        )
        if not isinstance(profile, dict):
            raise ValueError("GitHub returned an invalid profile response")
        if not isinstance(repositories, list) or not isinstance(events, list):
            raise ValueError("GitHub returned an invalid activity response")
        return build_github_snapshot(profile, repositories, events)


def save_github_snapshot(path: Path, snapshot: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_github_snapshot(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("GitHub context must contain a JSON object")
    if raw.get("schema_version") != GITHUB_CONTEXT_SCHEMA_VERSION:
        raise ValueError("unsupported GitHub context schema version")
    return raw


def github_integration_payload(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if snapshot is None:
        return {
            "connected": False,
            "source": "github_public",
            "account": None,
            "fetched_at": None,
            "active_repositories": [],
            "languages": [],
            "signals": {},
        }
    return {
        "connected": True,
        "source": snapshot.get("source"),
        "account": snapshot.get("account"),
        "fetched_at": snapshot.get("fetched_at"),
        "active_repositories": snapshot.get("active_repositories", []),
        "languages": snapshot.get("languages", []),
        "signals": snapshot.get("signals", {}),
    }


def disconnect_github(path: Path) -> None:
    if path.exists():
        path.unlink()
