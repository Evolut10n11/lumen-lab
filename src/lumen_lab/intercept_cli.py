from pathlib import Path

from .intercept import analyze_intercept
from .store import LabStore


def main() -> int:
    report = analyze_intercept(LabStore(Path.cwd()).load_outcomes())
    baseline = "n/a" if report.baseline_mae is None else f"{report.baseline_mae:.2f}"
    corrected = (
        "n/a"
        if report.loo_corrected_mae is None
        else f"{report.loo_corrected_mae:.2f}"
    )
    improvement = (
        "n/a"
        if report.improvement_ratio is None
        else f"{report.improvement_ratio:.2%}"
    )
    intercept = (
        "n/a"
        if report.proposed_intercept is None
        else f"{report.proposed_intercept:+.2f}"
    )

    print(f"Samples: {report.sample_size}")
    print(f"Baseline MAE: {baseline}")
    print(f"Leave-one-out corrected MAE: {corrected}")
    print(f"MAE improvement: {improvement}")
    print(f"Proposed full-sample intercept: {intercept}")
    print(f"Ranking preserved by constant shift: {report.ranking_preserved}")
    print(f"Direction: {report.direction}")
    print(f"Action: {report.action}")
    print(f"Recommendation: {report.recommendation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
