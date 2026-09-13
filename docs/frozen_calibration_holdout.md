# Frozen calibration holdout

`lumen-holdout` evaluates future outcomes against a calibration intercept that was frozen before those outcomes existed.

The repository-owned baseline lives at `state/calibration_baseline.json`. Its first version freezes the ten-outcome checkpoint after `exp-010` with intercept `+0.94` and the exact IDs used for training.

## Why freeze the baseline

Repeatedly recomputing an intercept on the same ledger can make historical error look better without proving that the correction generalizes. A frozen baseline prevents that form of leakage: outcomes whose IDs are not in the baseline training set are holdouts and are evaluated without changing the intercept.

The report includes:

- training and holdout counts;
- frozen intercept;
- holdout raw MAE;
- holdout intercept-corrected MAE;
- improvement ratio;
- per-holdout residual, raw error, and corrected error.

If there are no holdout outcomes, the command explicitly reports `no-holdout-evidence` instead of claiming calibration success.

## Safety and interpretation

The baseline is validated before use. Training IDs must be unique and present in the ledger, and the intercept must be finite. Evaluation never rewrites the baseline, `Experiment.score()`, or planner weights.

This is sequential project-specific holdout evidence, not an independent randomized benchmark. One improved holdout is useful evidence but is not enough to deploy the correction. The baseline should remain frozen while additional outcomes accumulate.

The command is local and deterministic and requires no model, network access, secret, or third-party statistics package.
