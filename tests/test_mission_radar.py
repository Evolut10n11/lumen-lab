import json

import pytest

from lumen_lab.mission_radar import Mission, load_missions, radar_snapshot, ranked_missions
from lumen_lab.mission_radar_cli import main


def mission(identifier: str, **overrides: object) -> Mission:
    data: dict[str, object] = {
        "id": identifier,
        "title": f"Mission {identifier}",
        "why_now": "Useful now",
        "next_action": "Do one concrete thing",
        "impact": 8,
        "urgency": 7,
        "leverage": 8,
        "momentum": 6,
        "effort": 5,
        "risk": 2,
        "status": "active",
    }
    data.update(overrides)
    return Mission.from_dict(data)


def write_state(tmp_path, items: list[dict[str, object]]):
    path = tmp_path / "missions.json"
    path.write_text(json.dumps(items), encoding="utf-8")
    return path


def test_loads_valid_missions(tmp_path) -> None:
    item = mission("alpha").to_dict()
    item.pop("score")
    path = write_state(tmp_path, [item])

    loaded = load_missions(path)

    assert loaded == [mission("alpha")]


def test_rejects_duplicate_ids(tmp_path) -> None:
    item = mission("alpha").to_dict()
    item.pop("score")
    path = write_state(tmp_path, [item, item])

    with pytest.raises(ValueError, match="duplicate mission id"):
        load_missions(path)


@pytest.mark.parametrize("field,value", [("impact", 0), ("risk", 11), ("effort", 4.5)])
def test_rejects_invalid_scores(field: str, value: object) -> None:
    with pytest.raises(ValueError, match=field):
        mission("bad", **{field: value})


def test_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="status"):
        mission("bad", status="running")


def test_ranking_rewards_value_and_penalizes_effort_and_risk() -> None:
    high = mission("high", impact=10, urgency=9, leverage=10, momentum=8, effort=4, risk=1)
    low = mission("low", impact=7, urgency=5, leverage=6, momentum=5, effort=9, risk=6)

    assert ranked_missions([low, high]) == [high, low]
    assert high.score > low.score


def test_ties_are_broken_by_id() -> None:
    beta = mission("beta")
    alpha = mission("alpha")

    assert ranked_missions([beta, alpha]) == [alpha, beta]


def test_done_and_paused_missions_are_not_ranked() -> None:
    active = mission("active")
    done = mission("done", status="done", impact=10, urgency=10, leverage=10, momentum=10)
    paused = mission("paused", status="paused", impact=10, urgency=10, leverage=10, momentum=10)

    assert ranked_missions([done, paused, active]) == [active]


def test_snapshot_limits_results() -> None:
    missions = [mission("a"), mission("b"), mission("c")]

    snapshot = radar_snapshot(missions, top=2)

    assert len(snapshot) == 2
    assert [item["id"] for item in snapshot] == ["a", "b"]


def test_snapshot_rejects_non_positive_top() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        radar_snapshot([mission("a")], top=0)


def test_cli_json_output(tmp_path, capsys) -> None:
    item = mission("alpha").to_dict()
    item.pop("score")
    path = write_state(tmp_path, [item])

    code = main(["--state", str(path), "--json"])
    output = json.loads(capsys.readouterr().out)

    assert code == 0
    assert output[0]["id"] == "alpha"
    assert output[0]["next_action"] == "Do one concrete thing"


def test_cli_is_read_only(tmp_path) -> None:
    item = mission("alpha").to_dict()
    item.pop("score")
    path = write_state(tmp_path, [item])
    before = path.read_bytes()

    assert main(["--state", str(path)]) == 0

    assert path.read_bytes() == before
