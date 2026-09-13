# Planner intercept calibration

`lumen-intercept` evaluates whether a single additive offset could improve the planner's absolute score calibration without changing relative experiment ordering.

The checkpoint is intentionally advisory. It never mutates `Experiment.score()` or planner weights.

## Method

For each recorded outcome, residual is `observed_score - expected_score`. The proposed full-sample intercept is the mean residual.

To avoid evaluating the correction on the same sample used to fit it, the checkpoint uses leave-one-out evaluation: each outcome is corrected with the mean residual of every *other* outcome. The report compares baseline MAE with this leave-one-out corrected MAE.

An intercept is supported only when all fixed gates pass:

- at least 6 recorded outcomes;
- absolute proposed intercept of at least 0.50;
- leave-one-out MAE improvement of at least 20%.

Otherwise the checkpoint rejects the correction or asks for more evidence.

## Ranking invariance

Adding the same constant `c` to every planner score preserves every pairwise difference:

`(score_a + c) - (score_b + c) = score_a - score_b`.

Therefore an additive intercept cannot change deterministic ranking order. This is why intercept calibration is evaluated separately from feature-weight calibration.

## Limits

Leave-one-out reduces self-fit leakage, but the outcomes are still a small, sequential, project-specific sample rather than independent production observations. A positive result justifies further evaluation, not automatic deployment. A scale error, nonlinear bias, or feature-specific bias will not be fixed by one constant.

The command is fully local and deterministic. It requires no model, network access, secret, or third-party statistics package.
