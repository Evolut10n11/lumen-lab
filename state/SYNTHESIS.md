# Lumen Synthesis

This snapshot is generated deterministically from repository state and journal text.
It does not use a model, network service, or secret, and it does not modify the journal.

## Evidence

- Completed experiments: 8
- Completed IDs: `exp-001`, `exp-002`, `exp-003`, `exp-004`, `exp-005`, `exp-006`, `exp-007`, `exp-008`
- Recorded outcomes: 8
- Journal sections: 9
- Calibration MAE: 1.08
- Mean signed residual: +1.08
- Calibration direction: systematic-underprediction

## Repeated lesson signals

- `deterministic-controls` — supported by `exp-001`, `exp-002`, `exp-004`, `exp-005`, `exp-006`, `exp-007`, `exp-008`
- `safety-boundaries` — supported by `exp-001`, `exp-002`, `exp-004`, `exp-005`, `exp-007`
- `tests-and-documentation` — supported by `exp-001`, `exp-002`, `exp-003`, `exp-004`, `exp-005`, `exp-006`, `exp-007`, `exp-008`

## Missing capabilities

No backlog capability is currently pending.

## Interpretation limits

- Lesson signals are keyword rules over recorded outcome summaries, not semantic claims.
- A signal is shown only when at least two distinct outcomes support it.
- Missing capabilities are the current ranked backlog, not generated recommendations.
- The journal remains the append-only narrative source; this file is a disposable view.
