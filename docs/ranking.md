# Planner ranking quality

`lumen-rankcheck` asks a different question from absolute calibration: does the planner put more successful experiments ahead of less successful ones?

The checkpoint compares every pair of recorded outcomes. For each pair it compares the sign of the predicted-score difference with the sign of the observed-score difference.

- matching signs are concordant;
- opposite signs are discordant;
- expected-score ties and observed-score ties are reported separately and excluded from the accuracy denominator.

Pairwise ordering accuracy is:

```text
concordant / (concordant + discordant)
```

The metric is local and deterministic. It requires no statistical package, model endpoint, network service, or secret.

## Decision policy

The current fixed thresholds are deliberately coarse:

1. Fewer than five outcomes or fewer than five comparable pairs: `insufficient-data`.
2. Accuracy at or above 70%: `ranking-supported`; hold relative planner weights.
3. Accuracy at or below 55%: `ranking-weak`; investigate feature contributions before changing coefficients.
4. Between those thresholds: `ranking-inconclusive`; hold weights and collect more varied outcomes.

The checkpoint never changes planner weights automatically.

## Why this is separate from calibration

A planner can be systematically too low or too high in absolute terms while still ordering candidates usefully. Conversely, a low mean calibration error does not guarantee useful ordering. Lumen therefore reports calibration MAE and mean signed residual alongside pairwise ranking quality, but does not combine them into one score.

With the first eight completed experiments, 21 pairs are comparable, 16 are concordant, 5 are discordant, and 7 are observed-score ties. Pairwise ordering accuracy is 76.19%, which supports keeping the relative weights unchanged even though all eight absolute predictions remain below their observed scores.

## Limits

Eight outcomes are still a small sample and several observed scores are tied. Pairwise accuracy does not identify which individual coefficient is correct, prove causal importance of a feature, or justify an automatic weight update. It is evidence about ordering only.
