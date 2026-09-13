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

Weights must not be changed from a single outcome. A future calibration step should require at least five completed experiments and should record the before/after weights in the journal.

The ledger is a learning aid, not an authority. Safety constraints and explicit repository rules always outrank a numeric score.
