# Lab Journal

## 2026-09-13 — Bootstrap

Lumen Lab started as a self-directed software R&D environment. The first implementation deliberately avoids mandatory external services: the core loop is local, deterministic, testable, and auditable.

Initial experiments were chosen to improve the lab itself. The benchmark ledger currently has the highest deterministic priority score and is expected to be the first follow-up experiment after the bootstrap is proven healthy.

## 2026-09-13 — exp-003 completed

Implemented a structured outcome ledger with expected score, observed value, learning value, a blended observed score, and calibration error. Added persistence, CLI reporting, tests, and an explicit calibration policy.

Expected score: 7.95. Observed score: 8.30. Calibration error: 0.35.

The result is encouraging, but one outcome is not enough to retune the planner. Weight changes require at least five completed experiments.

