from __future__ import annotations

import json
from pathlib import Path

from lumen_lab import encoding_recovery
from lumen_lab.encoding_recovery import (
    repair_mojibake_json,
    repair_mojibake_text,
    repair_workspace_json,
)


def _legacy_decode(value: str) -> str:
    return value.encode("utf-8").decode("cp1251")


def test_repeated_ambiguous_russian_letter_spans_fail_closed() -> None:
    assert repair_mojibake_text("Рё, Рё") == "Рё, Рё"
    assert repair_mojibake_text("РёРё") == "РёРё"
    assert repair_mojibake_text("«РёРё»") == "«РёРё»"
    assert repair_mojibake_text("РЁ РЁ") == "РЁ РЁ"


def test_ambiguous_keys_and_nested_json_are_preserved() -> None:
    payload = {
        "Рё, Рё": {
            "nested": ["РёРё", {"РЁ РЁ": "Рё, Рё"}],
        }
    }

    assert repair_mojibake_json(payload) == payload


def test_unambiguous_strong_mojibake_still_repairs() -> None:
    original = "Привет, мир"
    broken = _legacy_decode(original)

    assert repair_mojibake_text(broken) == original


def test_evidence_gated_weak_units_repair_outside_quotes_with_punctuation() -> None:
    broken_ya = _legacy_decode("Я")

    assert repair_mojibake_text(
        f"{broken_ya},",
        allow_single_units=True,
    ) == "Я,"
    assert repair_mojibake_text(
        f"({broken_ya})",
        allow_single_units=True,
    ) == "(Я)"
    assert repair_mojibake_text(
        f"[{broken_ya}]:",
        allow_single_units=True,
    ) == "[Я]:"


def test_v021_backup_proof_repairs_unquoted_punctuation_remnant(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "profile.json"
    broken_ya = _legacy_decode("Я")
    backup_payload = {
        "goal": f"{broken_ya},",
        "context": _legacy_decode("Работаю дизайнером"),
    }
    v021_live = encoding_recovery._repair_v021_json(backup_payload)
    assert v021_live == {
        "goal": f"{broken_ya},",
        "context": "Работаю дизайнером",
    }

    profile.write_text(json.dumps(v021_live, ensure_ascii=False), encoding="utf-8")
    backup = profile.with_name(f"{profile.name}.before-encoding-repair")
    backup.write_text(
        json.dumps(backup_payload, ensure_ascii=False),
        encoding="utf-8",
    )

    assert repair_workspace_json(tmp_path) == (profile,)
    assert json.loads(profile.read_text(encoding="utf-8")) == {
        "goal": "Я,",
        "context": "Работаю дизайнером",
    }
    assert json.loads(backup.read_text(encoding="utf-8")) == backup_payload


def test_v021_already_repaired_ambiguous_legacy_text_stays_stable(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "profile.json"
    broken = _legacy_decode("и, и")
    assert broken == "Рё, Рё"

    backup_payload = {broken: {"nested": [broken]}}
    v021_live = encoding_recovery._repair_v021_json(backup_payload)
    expected_live = {"и, и": {"nested": ["и, и"]}}
    assert v021_live == expected_live

    profile.write_text(json.dumps(v021_live, ensure_ascii=False), encoding="utf-8")
    backup = profile.with_name(f"{profile.name}.before-encoding-repair")
    backup.write_text(
        json.dumps(backup_payload, ensure_ascii=False),
        encoding="utf-8",
    )

    assert repair_workspace_json(tmp_path) == ()
    assert json.loads(profile.read_text(encoding="utf-8")) == expected_live
    assert json.loads(backup.read_text(encoding="utf-8")) == backup_payload
