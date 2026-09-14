from __future__ import annotations

import argparse
from pathlib import Path
from runpy import run_path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = run_path(str(ROOT / "packaging" / "check_engine_text.py"))
ASSERT_TIMING_BUDGET = SCRIPT["assert_timing_budget"]
POSITIVE_MILLISECONDS = SCRIPT["positive_milliseconds"]


def _timings(*samples: float) -> list[tuple[str, float]]:
    return [(f"sample-{index}", sample) for index, sample in enumerate(samples)]


def test_timing_budget_accepts_samples_within_limits() -> None:
    median_ms, max_ms = ASSERT_TIMING_BUDGET(
        _timings(900, 1100, 1300),
        max_median_ms=2500,
        max_sample_ms=5000,
    )

    assert median_ms == 1100
    assert max_ms == 1300


def test_timing_budget_rejects_median_regression() -> None:
    with pytest.raises(AssertionError, match="median exceeded"):
        ASSERT_TIMING_BUDGET(
            _timings(2600, 2700, 2800),
            max_median_ms=2500,
            max_sample_ms=5000,
        )


def test_timing_budget_rejects_single_slow_process() -> None:
    with pytest.raises(AssertionError, match="sample exceeded"):
        ASSERT_TIMING_BUDGET(
            _timings(900, 1000, 5100),
            max_median_ms=2500,
            max_sample_ms=5000,
        )


def test_timing_budget_remains_optional() -> None:
    assert ASSERT_TIMING_BUDGET(_timings(9000)) == (9000, 9000)


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "-inf"])
def test_cli_budget_values_must_be_positive_and_finite(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        POSITIVE_MILLISECONDS(value)


def test_cli_budget_accepts_positive_finite_value() -> None:
    assert POSITIVE_MILLISECONDS("2500") == 2500


def test_windows_workflow_applies_budget_to_both_engine_checks() -> None:
    workflow = (ROOT / ".github" / "workflows" / "windows-installer.yml").read_text(
        encoding="utf-8"
    )
    budget = "--max-median-ms 2500 --max-sample-ms 5000"

    assert workflow.count("packaging/check_engine_text.py") == 2
    assert workflow.count(budget) == 2
