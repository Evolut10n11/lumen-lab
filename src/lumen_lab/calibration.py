from .ledger import Outcome, mean_absolute_calibration_error


MIN_CALIBRATION_SAMPLES = 5
RESIDUAL_TOLERANCE = 0.05
MATERIAL_BIAS = 0.50


class CalibrationCheckpoint:
    __slots__ = (
        "sample_size",
        "mae",
        "mean_signed_error",
        "underpredicted",
        "overpredicted",
        "exact",
        "direction",
        "action",
        "recommendation",
    )

    def __init__(
        self,
        *,
        sample_size: int,
        mae: float | None,
        mean_signed_error: float | None,
        underpredicted: int,
        overpredicted: int,
        exact: int,
        direction: str,
        action: str,
        recommendation: str,
    ) -> None:
        self.sample_size = sample_size
        self.mae = mae
        self.mean_signed_error = mean_signed_error
        self.underpredicted = underpredicted
        self.overpredicted = overpredicted
        self.exact = exact
        self.direction = direction
        self.action = action
        self.recommendation = recommendation


def residual(outcome: Outcome) -> float:
    """Return observed minus expected score; positive means underprediction."""
    return round(outcome.observed_score() - outcome.expected_score, 2)


def analyze_calibration(outcomes: list[Outcome]) -> CalibrationCheckpoint:
    residuals = [residual(outcome) for outcome in outcomes]
    sample_size = len(residuals)
    underpredicted = sum(value > RESIDUAL_TOLERANCE for value in residuals)
    overpredicted = sum(value < -RESIDUAL_TOLERANCE for value in residuals)
    exact = sample_size - underpredicted - overpredicted
    mae = mean_absolute_calibration_error(outcomes)
    mean_signed_error = round(sum(residuals) / sample_size, 2) if sample_size else None

    if sample_size < MIN_CALIBRATION_SAMPLES:
        return CalibrationCheckpoint(
            sample_size=sample_size,
            mae=mae,
            mean_signed_error=mean_signed_error,
            underpredicted=underpredicted,
            overpredicted=overpredicted,
            exact=exact,
            direction="insufficient-data",
            action="collect-more-outcomes",
            recommendation=(
                f"Collect at least {MIN_CALIBRATION_SAMPLES} outcomes before considering "
                "a scoring change."
            ),
        )

    assert mean_signed_error is not None
    if underpredicted == sample_size and mean_signed_error >= MATERIAL_BIAS:
        direction = "systematic-underprediction"
        recommendation = (
            "All observed scores exceed their predictions. This is evidence of a global "
            "offset or scale mismatch, not evidence that any relative feature weight is "
            "wrong. Hold the weights and gather more varied outcomes before testing an "
            "intercept or scale adjustment."
        )
    elif overpredicted == sample_size and mean_signed_error <= -MATERIAL_BIAS:
        direction = "systematic-overprediction"
        recommendation = (
            "All observed scores fall below their predictions. This is evidence of a global "
            "offset or scale mismatch, not evidence that any relative feature weight is "
            "wrong. Hold the weights and gather more varied outcomes before testing an "
            "intercept or scale adjustment."
        )
    elif abs(mean_signed_error) < MATERIAL_BIAS:
        direction = "balanced-or-mixed"
        recommendation = (
            "Aggregate signed bias is small. Keep the current weights and collect more "
            "outcomes before attributing residuals to specific scoring features."
        )
    else:
        direction = "mixed-bias"
        recommendation = (
            "Residuals do not move uniformly. Keep the current weights until a later "
            "checkpoint can test residual association with impact, learning, feasibility, "
            "novelty, and risk separately."
        )

    return CalibrationCheckpoint(
        sample_size=sample_size,
        mae=mae,
        mean_signed_error=mean_signed_error,
        underpredicted=underpredicted,
        overpredicted=overpredicted,
        exact=exact,
        direction=direction,
        action="hold-weights",
        recommendation=recommendation,
    )
