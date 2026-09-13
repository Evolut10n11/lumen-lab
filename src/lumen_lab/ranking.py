from dataclasses import dataclass

from .ledger import Outcome, analyze_calibration

MIN_RANKING_SAMPLES = 5
MIN_COMPARABLE_PAIRS = 5
TIE_TOLERANCE = 0.05
SUPPORTED_ACCURACY = 0.70
WEAK_ACCURACY = 0.55


@dataclass(frozen=True, slots=True)
class RankingCheckpoint:
    sample_size: int
    total_pairs: int
    comparable_pairs: int
    expected_ties: int
    observed_ties: int
    concordant: int
    discordant: int
    accuracy: float | None
    calibration_mae: float | None
    mean_signed_residual: float | None
    direction: str
    action: str
    recommendation: str


def analyze_ranking(outcomes: list[Outcome]) -> RankingCheckpoint:
    sample_size = len(outcomes)
    total_pairs = sample_size * (sample_size - 1) // 2
    expected_ties = 0
    observed_ties = 0
    concordant = 0
    discordant = 0

    for index, left in enumerate(outcomes):
        for right in outcomes[index + 1 :]:
            expected_delta = left.expected_score - right.expected_score
            observed_delta = left.observed_score() - right.observed_score()
            if abs(expected_delta) <= TIE_TOLERANCE:
                expected_ties += 1
                continue
            if abs(observed_delta) <= TIE_TOLERANCE:
                observed_ties += 1
                continue
            if expected_delta * observed_delta > 0:
                concordant += 1
            else:
                discordant += 1

    comparable_pairs = concordant + discordant
    accuracy = (
        round(concordant / comparable_pairs, 4) if comparable_pairs else None
    )
    calibration = analyze_calibration(outcomes)

    if (
        sample_size < MIN_RANKING_SAMPLES
        or comparable_pairs < MIN_COMPARABLE_PAIRS
    ):
        direction = "insufficient-data"
        action = "collect-more-outcomes"
        recommendation = (
            "Collect more outcomes before judging relative planner ordering. "
            "Absolute calibration and ranking quality remain separate questions."
        )
    elif accuracy is not None and accuracy >= SUPPORTED_ACCURACY:
        direction = "ranking-supported"
        action = "hold-relative-weights"
        recommendation = (
            "Pairwise ordering is supported by the current evidence. Keep the relative "
            "planner weights unchanged while treating absolute score bias separately."
        )
    elif accuracy is not None and accuracy <= WEAK_ACCURACY:
        direction = "ranking-weak"
        action = "investigate-feature-weights"
        recommendation = (
            "Pairwise ordering is weak. Investigate which scoring features contribute "
            "to discordant pairs before changing any coefficient."
        )
    else:
        direction = "ranking-inconclusive"
        action = "hold-and-collect"
        recommendation = (
            "Pairwise ordering evidence is inconclusive. Keep the current weights and "
            "collect more varied outcomes before retuning."
        )

    return RankingCheckpoint(
        sample_size=sample_size,
        total_pairs=total_pairs,
        comparable_pairs=comparable_pairs,
        expected_ties=expected_ties,
        observed_ties=observed_ties,
        concordant=concordant,
        discordant=discordant,
        accuracy=accuracy,
        calibration_mae=calibration.mae,
        mean_signed_residual=calibration.mean_signed_error,
        direction=direction,
        action=action,
        recommendation=recommendation,
    )
