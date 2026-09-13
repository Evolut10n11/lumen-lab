from lumen_lab.github_bridge import RemoteIssue, desired_issues, issue_spec, plan_sync
from lumen_lab.models import Experiment


def experiment(
    experiment_id: str = "exp-001",
    *,
    status: str = "backlog",
    title: str = "GitHub Issues bridge",
) -> Experiment:
    return Experiment(
        id=experiment_id,
        title=title,
        hypothesis="Make autonomous work visible and steerable.",
        impact=8,
        learning=7,
        feasibility=8,
        novelty=5,
        risk=2,
        status=status,
    )


def test_issue_spec_contains_stable_marker_and_planner_snapshot() -> None:
    spec = issue_spec(experiment())

    assert spec.title == "[lumen:exp-001] GitHub Issues bridge"
    assert "<!-- lumen-lab:exp-001 -->" in spec.body
    assert "priority score: `6.75`" in spec.body
    assert "state: `backlog`" in spec.body


def test_desired_issues_only_contains_pending_work() -> None:
    experiments = [
        experiment("exp-001", status="backlog"),
        experiment("exp-002", status="active"),
        experiment("exp-003", status="done"),
        experiment("exp-004", status="dropped"),
    ]

    assert [item.experiment_id for item in desired_issues(experiments)] == [
        "exp-001",
        "exp-002",
    ]


def test_plan_creates_missing_managed_issue() -> None:
    actions = plan_sync([experiment()], [])

    assert len(actions) == 1
    assert actions[0].kind == "create"
    assert actions[0].experiment_id == "exp-001"
    assert actions[0].issue_number is None


def test_plan_updates_existing_managed_issue_when_snapshot_changes() -> None:
    item = experiment()
    remote = RemoteIssue(
        number=17,
        title="old title",
        body="<!-- lumen-lab:exp-001 -->\nold body",
    )

    actions = plan_sync([item], [remote])

    assert len(actions) == 1
    assert actions[0].kind == "update"
    assert actions[0].issue_number == 17


def test_plan_is_noop_when_managed_issue_matches() -> None:
    spec = issue_spec(experiment())
    remote = RemoteIssue(number=17, title=spec.title, body=spec.body)

    assert plan_sync([experiment()], [remote]) == []


def test_unmanaged_issue_is_never_updated_even_with_similar_title() -> None:
    remote = RemoteIssue(
        number=21,
        title="[lumen:exp-001] GitHub Issues bridge",
        body="Human-created issue without a management marker.",
    )

    actions = plan_sync([experiment()], [remote])

    assert len(actions) == 1
    assert actions[0].kind == "create"
    assert actions[0].issue_number is None


def test_done_experiment_does_not_close_remote_issue() -> None:
    remote = RemoteIssue(
        number=33,
        title="[lumen:exp-001] GitHub Issues bridge",
        body="<!-- lumen-lab:exp-001 -->\nmanaged",
    )

    assert plan_sync([experiment(status="done")], [remote]) == []
