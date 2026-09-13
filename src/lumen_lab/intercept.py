from dataclasses import dataclass

from .ledger import Outcome, residual

MIN_INTERCEPT_SAMPLES = 6
MIN_MAE_IMPROVEMENT = 0.20
MIN_MATERIAL_INTERCEPT = 0.50


@dataclass(frozen=True, slots=True)
class InterceptCheckpoint:
    sample_size: int
    baseline_mae: float | None
    loo_corrected_mae: float | None
    improvement_ratio: float | None
    proposed_intercept: float | None
    ranking_preserved: bool
    direction: str
    action: str
    recommendation: str


def _mean_absolute(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(abs(value) for value in values) / len(values)


def analyze_intercept(outcomes: list[Outcome]) -> InterceptCheckpoint:
    residuals = [residual(outcome) for outcome in outcomes]
    sample_size = len(residuals)
    baseline_raw = _mean_absolute(residuals)
    proposed_raw = sum(residuals) / sample_size if sample_size else None

    loo_raw: float | None = None
    if sample_size >= 2:
        total = sum(residuals)
        loo_errors = [
            abs(value - (total - value) / (sample_size - 1))
            for value in residuals
        ]
        loo_raw = sum(loo_errors) / sample_size

    improvement_ratio: float | None = None
    if baseline_raw is not None and loo_raw is not None:
        if baseline_raw == 0:
            improvement_ratio = 0.0
        else:
            improvement_ratio = round((baseline_raw - loo_raw) / baseline_raw, 4)

    baseline_mae = None if baseline_raw is None else round(baseline_raw, 2)
    loo_corrected_mae = None if loo_raw is None else round(loo_raw, 2)
    proposed_intercept = None if proposed_raw is None else round(proposed_raw, 2)

    if sample_size < MIN_INTERCEPT_SAMPLES:
        direction = "insufficient-data"
        action = "collect-more-outcomes"
        recommendation = (
            f"Collect at least {MIN_INTERCEPT_SAMPLES} outcomes before evaluating an "
            "additive calibration intercept."
        )
    elif (
        proposed_raw is not None
        and improvement_ratio is not None
        and abs(proposed_raw) >= MIN_MATERIAL_INTERCEPT
        and improvement_ratio >= MIN_MAE_IMPROVEMENT
    ):
        direction = "intercept-supported"
        action = "consider-intercept-advisory"
        recommendation = (
            "Leave-one-out evidence supports an additive intercept for absolute score "
            "calibration. Keep it advisory until more outcomes confirm the gain; adding "
            "one constant to every score does not change relative ranking order."
        )
    else:
        direction = "intercept-rejected"
        action = "hold-current-scale"
        recommendation = (
            "The additive correction does not clear the fixed material-offset and "
            "leave-one-out improvement thresholds. Keep the current score scale and "
            "collect more varied outcomes."
        )

    return InterceptCheckpoint(
        sample_size=sample_size,
        baseline_mae=baseline_mae,
        loo_corrected_mae=loo_corrected_mae,
        improvement_ratio=improvement_ratio,
        proposed_intercept=proposed_intercept,
        ranking_preserved=True,
        direction=direction,
        action=action,
        recommendation=recommendation,
    )
