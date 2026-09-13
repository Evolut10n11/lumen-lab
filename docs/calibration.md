# Planner calibration

The outcome ledger compares an experiment's predicted priority score with an observed score after completion.

Observed score is intentionally simple:

```text
0.70 * observed value + 0.30 * learning value
```

The first aggregate signal is mean absolute calibration error (MAE).

## How to use it

- MAE below 1.0: keep the current scoring weights unless repeated evidence suggests a specific bias.
- MAE from 1.0 to 2.0: inspect recent outcomes for systematic over- or under-estimation before changing weights.
- MAE above 2.0: treat planner rankings as weak evidence and prioritize a calibration experiment before adding more autonomy.

Weights must not be changed from a single outcome. A calibration checkpoint requires at least five completed experiments.

## Calibration checkpoint

`lumen calibrate` summarizes residuals where:

```text
residual = observed score - expected score
```

A positive residual means the planner underpredicted the result; a negative residual means it overpredicted it. The checkpoint reports sample size, MAE, mean signed residual, and under/over/exact counts.

The decision policy is deliberately conservative:

1. Fewer than five outcomes means `insufficient-data`; collect more evidence and do not change scoring.
2. If every residual points in the same direction and the mean signed error is material, classify it as systematic under- or over-prediction.
3. Uniform direction is treated as evidence for a possible global offset or scale mismatch, not as evidence that the relative feature weights are wrong.
4. Mixed residuals are not enough to retune weights either. A later checkpoint must test whether residuals are associated with impact, learning, feasibility, novelty, or risk before changing those coefficients.
5. The checkpoint never mutates weights automatically. Its current action is either `collect-more-outcomes` or `hold-weights`.

For the first five Lumen outcomes, all five observed scores exceed their predictions. The mean signed residual is therefore positive and equal to the current MAE, which is a clear underprediction signal. Because the direction is uniform across heterogeneous experiments, the correct action is to hold the relative weights and collect more varied evidence rather than retune coefficients immediately.

The ledger is a learning aid, not an authority. Safety constraints and explicit repository rules always outrank a numeric score.
