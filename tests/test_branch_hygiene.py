from lumen_lab.branch_hygiene import GitHubApi, PullRequestRef, cleanup_candidates


def pr(
    number: int,
    *,
    state: str = "closed",
    merged: bool = False,
    head: str,
    body: str = "",
    repo: str = "Evolut10n11/lumen-lab",
) -> PullRequestRef:
    return PullRequestRef(
        number=number,
        state=state,
        merged_at="2026-09-13T00:00:00Z" if merged else None,
        head_ref=head,
        head_repo=repo,
        body=body,
    )


def branch(name: str, *, protected: bool = False) -> dict[str, object]:
    return {"name": name, "protected": protected}


def test_cleanup_candidates_delete_merged_superseded_and_rebased_predecessors() -> None:
    branches = [
        branch("main", protected=True),
        branch("merged-feature"),
        branch("replacement"),
        branch("superseded-feature"),
        branch("profile-work"),
        branch("profile-work-rebased"),
        branch("docs-readme-product-guide"),
    ]
    pull_requests = [
        pr(1, merged=True, head="merged-feature"),
        pr(2, head="superseded-feature"),
        pr(3, merged=True, head="replacement", body="Supersedes #2 after main advanced."),
        pr(
            4,
            merged=True,
            head="profile-work-rebased",
            body="Rebased onto current main before merge.",
        ),
    ]

    assert cleanup_candidates(
        repository="Evolut10n11/lumen-lab",
        default_branch="main",
        branches=branches,
        pull_requests=pull_requests,
    ) == [
        "merged-feature",
        "profile-work",
        "profile-work-rebased",
        "replacement",
        "superseded-feature",
    ]


def test_cleanup_candidates_preserve_default_open_protected_and_unrelated_branches() -> None:
    branches = [
        branch("main", protected=True),
        branch("active-feature"),
        branch("protected-release", protected=True),
        branch("unrelated-wip"),
        branch("merged-feature"),
    ]
    pull_requests = [
        pr(1, state="open", head="active-feature"),
        pr(2, merged=True, head="protected-release"),
        pr(3, merged=True, head="merged-feature"),
        pr(4, merged=True, head="fork-feature", repo="someone/fork"),
    ]

    assert cleanup_candidates(
        repository="Evolut10n11/lumen-lab",
        default_branch="main",
        branches=branches,
        pull_requests=pull_requests,
    ) == ["merged-feature"]


def test_supersedes_reference_only_applies_from_a_merged_pr() -> None:
    branches = [branch("main"), branch("old"), branch("new")]
    pull_requests = [
        pr(1, head="old"),
        pr(2, head="new", body="Supersedes #1"),
    ]

    assert cleanup_candidates(
        repository="Evolut10n11/lumen-lab",
        default_branch="main",
        branches=branches,
        pull_requests=pull_requests,
    ) == []


def test_delete_branch_uses_ref_path_with_branch_slashes(monkeypatch) -> None:
    api = GitHubApi("Evolut10n11/lumen-lab", "token")
    calls: list[tuple[str, str]] = []

    def fake_request(path: str, *, method: str = "GET") -> None:
        calls.append((path, method))

    monkeypatch.setattr(api, "_request", fake_request)
    api.delete_branch("feat/example branch")

    assert calls == [
        (
            "/repos/Evolut10n11/lumen-lab/git/refs/heads/feat/example%20branch",
            "DELETE",
        )
    ]
