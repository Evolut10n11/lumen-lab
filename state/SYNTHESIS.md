# Lumen Synthesis

This snapshot is generated deterministically from repository state and journal text.
It does not use a model, network service, or secret, and it does not modify the journal.

## Evidence

- Completed experiments: 13
- Completed IDs: `exp-001`, `exp-002`, `exp-003`, `exp-004`, `exp-005`, `exp-006`, `exp-007`, `exp-008`, `exp-009`, `exp-010`, `exp-011`, `exp-012`, `exp-013`
- Recorded outcomes: 13
- Journal sections: 14
- Calibration MAE: 0.87
- Mean signed residual: +0.87
- Calibration direction: systematic-underprediction

## Repeated lesson signals

- `deterministic-controls` — supported by `exp-001`, `exp-002`, `exp-004`, `exp-005`, `exp-006`, `exp-007`, `exp-008`, `exp-009`, `exp-010`, `exp-011`, `exp-012`, `exp-013`
- `safety-boundaries` — supported by `exp-001`, `exp-002`, `exp-004`, `exp-005`, `exp-007`
- `tests-and-documentation` — supported by `exp-001`, `exp-002`, `exp-003`, `exp-004`, `exp-005`, `exp-006`, `exp-007`, `exp-008`, `exp-009`, `exp-010`, `exp-011`, `exp-012`, `exp-013`

## Missing capabilities

- `exp-015` — Experiment provenance index — priority `7.60`
- `exp-014` — State schema versioning — priority `7.45`

## Interpretation limits

- Lesson signals are keyword rules over recorded outcome summaries, not semantic claims.
- A signal is shown only when at least two distinct outcomes support it.
- Missing capabilities are the current ranked backlog, not generated recommendations.
- The journal remains the append-only narrative source; this file is a disposable view.
