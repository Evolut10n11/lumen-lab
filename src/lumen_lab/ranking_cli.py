from pathlib import Path

from .ranking import analyze_ranking
from .store import LabStore


def main() -> int:
    report = analyze_ranking(LabStore(Path.cwd()).load_outcomes())
    accuracy = "n/a" if report.accuracy is None else f"{report.accuracy:.2%}"
    mae = (
        "n/a"
        if report.calibration_mae is None
        else f"{report.calibration_mae:.2f}"
    )
    signed = (
        "n/a"
        if report.mean_signed_residual is None
        else f"{report.mean_signed_residual:+.2f}"
    )

    print(f"Samples: {report.sample_size}")
    print(f"Total pairs: {report.total_pairs}")
    print(f"Comparable pairs: {report.comparable_pairs}")
    print(
        "Pair counts: "
        f"concordant={report.concordant} discordant={report.discordant} "
        f"expected_ties={report.expected_ties} observed_ties={report.observed_ties}"
    )
    print(f"Pairwise ordering accuracy: {accuracy}")
    print(f"Absolute calibration MAE: {mae}")
    print(f"Mean signed residual: {signed}")
    print(f"Direction: {report.direction}")
    print(f"Action: {report.action}")
    print(f"Recommendation: {report.recommendation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
