from pathlib import Path

from .holdout import analyze_holdout, load_baseline
from .store import LabStore


def main() -> int:
    root = Path.cwd()
    baseline_path = root / "state" / "calibration_baseline.json"
    try:
        baseline = load_baseline(baseline_path)
        report = analyze_holdout(LabStore(root).load_outcomes(), baseline)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    raw = "n/a" if report.raw_mae is None else f"{report.raw_mae:.2f}"
    corrected = "n/a" if report.corrected_mae is None else f"{report.corrected_mae:.2f}"
    improvement = (
        "n/a"
        if report.improvement_ratio is None
        else f"{report.improvement_ratio:.2%}"
    )

    print(f"Frozen training outcomes: {report.training_count}")
    print(f"Holdout outcomes: {report.holdout_count}")
    print(f"Frozen intercept: {report.intercept:+.2f}")
    print(f"Holdout raw MAE: {raw}")
    print(f"Holdout corrected MAE: {corrected}")
    print(f"Holdout improvement: {improvement}")
    for item in report.observations:
        print(
            f"{item.experiment_id}: residual={item.residual:+.2f} "
            f"raw_error={item.raw_error:.2f} corrected_error={item.corrected_error:.2f}"
        )
    print(f"Direction: {report.direction}")
    print(f"Action: {report.action}")
    print(f"Recommendation: {report.recommendation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
