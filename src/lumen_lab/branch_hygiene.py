from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

API_ROOT = "https://api.github.com"
SUPERSEDES_RE = re.compile(r"\bsupersedes\s+#(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class PullRequestRef:
    number: int
    state: str
    merged_at: str | None
    head_ref: str
    head_repo: str | None
    body: str

    @property
    def merged(self) -> bool:
        return self.merged_at is not None


class GitHubApi:
    def __init__(self, repository: str, token: str) -> None:
        self.repository = repository
        self.token = token

    def _request(self, path: str, *, method: str = "GET") -> Any:
        request = urllib.request.Request(
            f"{API_ROOT}{path}",
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "lumen-lab-branch-hygiene",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if method == "DELETE" and exc.code == 404:
                return None
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub API {method} {path} failed: {exc.code} {detail}") from exc
        if not raw:
            return None
        return json.loads(raw)

    def _paged(self, path: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        separator = "&" if "?" in path else "?"
        while True:
            batch = self._request(f"{path}{separator}per_page=100&page={page}")
            if not isinstance(batch, list):
                raise RuntimeError(f"expected a list from GitHub API path {path}")
            items.extend(item for item in batch if isinstance(item, dict))
            if len(batch) < 100:
                return items
            page += 1

    def branches(self) -> list[dict[str, Any]]:
        return self._paged(f"/repos/{self.repository}/branches")

    def pull_requests(self) -> list[PullRequestRef]:
        raw = self._paged(f"/repos/{self.repository}/pulls?state=all")
        pull_requests: list[PullRequestRef] = []
        for item in raw:
            head = item.get("head") or {}
            head_repo = head.get("repo") or {}
            pull_requests.append(
                PullRequestRef(
                    number=int(item["number"]),
                    state=str(item.get("state", "")),
                    merged_at=item.get("merged_at"),
                    head_ref=str(head.get("ref", "")),
                    head_repo=head_repo.get("full_name"),
                    body=str(item.get("body") or ""),
                )
            )
        return pull_requests

    def delete_branch(self, branch: str) -> None:
        encoded_branch = urllib.parse.quote(branch, safe="/")
        self._request(
            f"/repos/{self.repository}/git/refs/heads/{encoded_branch}",
            method="DELETE",
        )


def cleanup_candidates(
    *,
    repository: str,
    default_branch: str,
    branches: list[dict[str, Any]],
    pull_requests: list[PullRequestRef],
) -> list[str]:
    branch_names = {
        str(item.get("name", ""))
        for item in branches
        if isinstance(item.get("name"), str) and item.get("name")
    }
    protected = {
        str(item["name"])
        for item in branches
        if item.get("protected") is True and isinstance(item.get("name"), str)
    }
    open_heads = {
        pr.head_ref
        for pr in pull_requests
        if pr.state == "open" and pr.head_repo == repository and pr.head_ref
    }
    by_number = {pr.number: pr for pr in pull_requests}

    candidates: set[str] = set()
    for pr in pull_requests:
        if not pr.merged or pr.head_repo != repository or not pr.head_ref:
            continue
        candidates.add(pr.head_ref)

        for superseded_number in SUPERSEDES_RE.findall(pr.body):
            superseded = by_number.get(int(superseded_number))
            if (
                superseded is not None
                and superseded.state == "closed"
                and superseded.head_repo == repository
                and superseded.head_ref
            ):
                candidates.add(superseded.head_ref)

        if pr.head_ref.endswith("-rebased") and "rebas" in pr.body.casefold():
            candidates.add(pr.head_ref.removesuffix("-rebased"))

    candidates &= branch_names
    candidates -= open_heads
    candidates -= protected
    candidates.discard(default_branch)
    return sorted(candidates)


def run(*, apply: bool, repository: str, token: str, default_branch: str) -> int:
    api = GitHubApi(repository, token)
    branches = api.branches()
    pull_requests = api.pull_requests()
    candidates = cleanup_candidates(
        repository=repository,
        default_branch=default_branch,
        branches=branches,
        pull_requests=pull_requests,
    )

    mode = "apply" if apply else "dry-run"
    print(f"Branch hygiene ({mode}): {len(candidates)} removable branch(es)")
    for branch in candidates:
        print(f"- {branch}")
        if apply:
            api.delete_branch(branch)

    if apply:
        print(f"Deleted {len(candidates)} branch(es).")
    else:
        print("No branches were changed. Use --apply to delete the listed branches.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Delete only merged or explicitly superseded same-repository branches."
    )
    parser.add_argument("--apply", action="store_true", help="perform deletions")
    parser.add_argument(
        "--repository",
        default=os.getenv("GITHUB_REPOSITORY", ""),
        help="owner/repo; defaults to GITHUB_REPOSITORY",
    )
    parser.add_argument(
        "--default-branch",
        default="main",
        help="branch that must never be deleted",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token = os.getenv("GITHUB_TOKEN", "")
    if not args.repository:
        print("error: repository is required", file=sys.stderr)
        return 2
    if not token:
        print("error: GITHUB_TOKEN is required", file=sys.stderr)
        return 2
    return run(
        apply=args.apply,
        repository=args.repository,
        token=token,
        default_branch=args.default_branch,
    )


if __name__ == "__main__":
    raise SystemExit(main())
