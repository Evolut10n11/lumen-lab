from pathlib import Path

from .calibration import analyze_calibration
from .store import LabStore


def main() -> int:
    report = analyze_calibration(LabStore(Path.cwd()).load_outcomes())
    mae = "n/a" if report.mae is None else f"{report.mae:.2f}"
    signed = (
        "n/a"
        if report.mean_signed_error is None
        else f"{report.mean_signed_error:+.2f}"
    )

    print(f"Samples: {report.sample_size}")
    print(f"MAE: {mae}")
    print(f"Mean signed residual: {signed}")
    print(
        "Residual counts: "
        f"under={report.underpredicted} over={report.overpredicted} exact={report.exact}"
    )
    print(f"Direction: {report.direction}")
    print(f"Action: {report.action}")
    print(f"Recommendation: {report.recommendation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
