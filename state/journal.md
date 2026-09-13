# Lab Journal

## 2026-09-13 — Bootstrap

Lumen Lab started as a self-directed software R&D environment. The first implementation deliberately avoids mandatory external services: the core loop is local, deterministic, testable, and auditable.

Initial experiments were chosen to improve the lab itself. The benchmark ledger currently has the highest deterministic priority score and is expected to be the first follow-up experiment after the bootstrap is proven healthy.

## 2026-09-13 — exp-003 completed

Implemented a structured outcome ledger with expected score, observed value, learning value, a blended observed score, and calibration error. Added persistence, CLI reporting, tests, and an explicit calibration policy.

Expected score: 7.95. Observed score: 8.30. Calibration error: 0.35.

The result is encouraging, but one outcome is not enough to retune the planner. Weight changes require at least five completed experiments.

## 2026-09-13 — exp-001 completed

Implemented a conservative GitHub Issues bridge for pending experiments. The bridge uses deterministic ownership markers, defaults to zero-network dry-run mode, requires explicit repository and authentication for writes, and only creates or updates issues that it can prove it owns. It never closes issues or mutates unmarked human-owned issues.

Expected score: 6.75. Observed score: 8.00. Calibration error: 1.25.

The experiment delivered more operational value than the planner predicted, especially because visibility and steerability can now be added without making GitHub a hidden source of truth. Two outcomes are still insufficient to retune planner weights; the five-outcome minimum remains in force.

## 2026-09-13 — exp-002 completed

Implemented an optional provider-neutral LLM planning adapter around OpenAI-compatible chat-completions endpoints. The deterministic planner remains the default and fallback, local endpoints require no secret, and model output is constrained to existing backlog IDs before it can influence a recommendation. Added `lumen advise`, transport injection for tests, local-model documentation, and failure-safe behavior for malformed responses, unknown IDs, timeouts, and network errors.

Expected score: 6.65. Observed score: 8.30. Calibration error: 1.65.

The qualitative planner layer adds useful flexibility without becoming authoritative or mutating state. Three outcomes are still below the five-outcome threshold required before any planner weight changes.

## 2026-09-13 — exp-004 completed

Implemented the constrained experiment execution layer. Commands use argv with `shell=False`, executable names require an explicit allowlist, every run receives a fresh temporary working directory and a minimal environment, stdin is disabled, runtime is bounded, and stdout/stderr are drained concurrently with bounded in-memory capture. Structured JSON results are available through `lumen sandbox`.

Expected score: 6.20. Observed score: 8.30. Calibration error: 2.10.

The main learning was also a boundary: subprocess containment is useful for removing ambient authority, but it is not an OS security sandbox. Allowed programs still retain the current user's operating-system permissions, so hostile code requires a container, VM, or OS-enforced sandbox. The original four-experiment bootstrap backlog is now complete. Four outcomes remain below the five-outcome threshold required before planner weight changes.

## 2026-09-13 — exp-005 completed

Implemented a deterministic backlog replenishment gate. `lumen replenish` is dry-run by default, refuses to operate while backlog or active work exists, validates every curated candidate through the normal experiment schema, and never overwrites an existing experiment ID. State mutation requires explicit `--apply` and remains local with no network, model endpoint, or secret requirement.

Expected score: 8.20. Observed score: 9.00. Calibration error: 0.80. Five-outcome calibration MAE: 1.23.

The lab now has enough completed outcomes to satisfy the minimum evidence threshold for a calibration review, but the weights were intentionally not changed inside the same experiment that crossed the threshold. Replenishment produced three second-generation candidates: `exp-006` planner calibration checkpoint, `exp-007` sandbox capability manifests, and `exp-008` journal synthesis snapshot. Deterministic ranking makes `exp-006` the next candidate with score 7.85.

## 2026-09-13 — exp-006 completed

Implemented a deterministic planner calibration checkpoint that reports residuals as observed minus expected score, sample size, MAE, mean signed residual, and directional counts. Added explicit classifications for insufficient evidence, systematic underprediction, systematic overprediction, and mixed residuals, plus the `lumen-calibrate` command, tests, and calibration policy documentation.

Before recording this experiment, the first five outcomes had MAE 1.23 and mean signed residual +1.23: all 5/5 observed scores exceeded their predictions. The checkpoint classifies this as systematic underprediction, but treats the uniform direction as evidence of a possible global offset or scale mismatch rather than evidence that the relative impact, learning, feasibility, novelty, or risk weights are wrong. Action: hold weights and collect more varied evidence.

Expected score: 7.85. Observed score: 8.60. Calibration error: 0.75. Six-outcome calibration MAE: 1.15.

No planner coefficient was changed. The highest remaining backlog item is now `exp-008` journal synthesis snapshot with score 7.60, ahead of `exp-007` sandbox capability manifests at 6.95.

