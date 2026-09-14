from __future__ import annotations

import json
from pathlib import Path

import pytest

import lumen_lab.state_io as state_io


def test_atomic_json_write_preserves_unicode(tmp_path: Path) -> None:
    path = tmp_path / "state" / "profile.json"

    state_io.write_json_atomic(path, {"name": "Люмен"})

    assert json.loads(path.read_text(encoding="utf-8")) == {"name": "Люмен"}


def test_failed_atomic_replace_preserves_previous_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "state.json"
    path.write_text('{"value": "old"}\n', encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(state_io.os, "replace", fail_replace)

    with pytest.raises(OSError, match="simulated replace failure"):
        state_io.write_json_atomic(path, {"value": "new"})

    assert json.loads(path.read_text(encoding="utf-8")) == {"value": "old"}
    assert list(tmp_path.glob(".*.tmp")) == []
