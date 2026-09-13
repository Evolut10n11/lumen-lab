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

## 2026-09-13 — exp-008 completed

Implemented a deterministic synthesis snapshot over structured experiment state, recorded outcomes, and journal section metadata. The new `lumen-synthesize` command previews by default and requires `--write` to create or replace only `state/SYNTHESIS.md`; it never rewrites the append-only journal. Repeated lesson signals require support from at least two recorded outcome summaries and always expose their supporting experiment IDs.

The first synthesis surfaces repeated themes around deterministic controls, explicit safety boundaries, and tests/documentation while preserving provenance instead of turning the generated snapshot into a new source of truth. Missing capabilities come only from the validated ranked backlog, so synthesis does not invent autonomous work.

Expected score: 7.60. Observed score: 8.30. Calibration error: 0.70. Seven-outcome calibration MAE: 1.09.

The only remaining backlog item is now `exp-007` sandbox capability manifests with score 6.95.

## 2026-09-13 — exp-007 completed

Implemented named capability manifests as a deterministic audit layer over the existing constrained subprocess runner. Manifests reuse the same bare-executable validation, carry bounded timeout/output policy, can be listed without execution, and cannot be mixed with manual allowlist or limit overrides. The original `lumen sandbox --allow ...` path remains available for explicit one-off runs.

The repository now includes a conservative `python-basic` example and tests for duplicate names, path-like executable rejection, missing profiles, deterministic listing, manual/manifest conflicts, and real manifest-backed execution. Manifests remain convenience and policy objects rather than an OS security boundary.

Expected score: 6.95. Observed score: 8.00. Calibration error: 1.05. Eight-outcome calibration MAE: 1.08.

All eight recorded experiments still landed above their predicted scores, so the systematic-underprediction signal remains. The current validated backlog is now empty; the next planning cycle should define a third generation of measured experiments rather than silently broadening capabilities.

## 2026-09-13 — exp-009 completed

Implemented a deterministic planner ranking-quality checkpoint that evaluates expected versus observed ordering pair by pair while excluding ties from the accuracy denominator. The `lumen-rankcheck` command reports concordant, discordant, comparable, and tied pairs alongside absolute calibration metrics so ranking quality is not confused with score calibration.

Across the first eight outcomes, 21 pairs are comparable: 16 concordant and 5 discordant, with 7 observed-score ties. Pairwise ordering accuracy is 76.19%, which meets the fixed `ranking-supported` threshold. This supports keeping relative planner weights unchanged even though absolute predictions remain systematically low.

Expected score: 8.75. Observed score: 9.00. Calibration error: 0.25. Nine-outcome calibration MAE: 0.99.

The result strengthens the case for treating current bias as an absolute-scale problem rather than immediately retuning feature coefficients. Future planner work should investigate an intercept or scale correction separately from ranking weights.

## 2026-09-13 — exp-010 completed

Implemented an advisory additive-intercept calibration checkpoint with leave-one-out evaluation so each held-out outcome is corrected using only residuals from the other outcomes. The new `lumen-intercept` command reports baseline MAE, leave-one-out corrected MAE, improvement, proposed full-sample intercept, ranking invariance, and a fixed-threshold recommendation.

Across the first nine outcomes, baseline MAE is 0.99 and leave-one-out corrected MAE is 0.52, a 47.05% improvement. The proposed full-sample intercept is +0.99. Adding a single constant preserves every pairwise score difference, so the 76.19% ranking-quality evidence from exp-009 is not disturbed.

Expected score: 8.10. Observed score: 8.60. Calibration error: 0.50. Ten-outcome calibration MAE: 0.94.

The intercept is intentionally not applied to `Experiment.score()`. Current evidence supports keeping it advisory until more outcomes confirm that the absolute-scale correction generalizes beyond this small sequential sample.

## 2026-09-13 — exp-011 completed

Implemented a frozen calibration baseline and deterministic holdout evaluator. The baseline captures intercept `+0.94` and the exact ten experiment IDs used to estimate it; future evaluation partitions outcomes by ID and never refits or rewrites that baseline. `lumen-holdout` reports raw and corrected holdout errors with per-experiment provenance.

After implementation CI passed, `exp-011` became the first outcome outside the frozen training set. Its raw planner error is 0.55; applying the frozen intercept produces error 0.39, a 29.09% improvement. This is the first genuinely forward observation supporting the absolute-scale correction, but one holdout is intentionally not treated as deployment evidence.

Expected score: 8.05. Observed score: 8.60. Calibration error: 0.55. Eleven-outcome calibration MAE: 0.90.

The frozen baseline remains unchanged. Additional experiments can now accumulate comparable holdout evidence without contaminating the calibration estimate.

## 2026-09-13 — exp-012 completed

Replaced the exhausted source-code candidate tuple with a repository-owned declarative registry. `state/candidates.json` is validated through the normal Experiment schema, rejects duplicate IDs and non-backlog statuses, filters IDs already present in the backlog, and ranks remaining candidates deterministically before dry-run or explicit apply.

The previous `exp-006`, `exp-007`, and `exp-008` templates remain in the registry as provenance while the next curated generation adds `exp-013` state integrity doctor, `exp-015` experiment provenance index, and `exp-014` state schema versioning. The registry itself is never consumed or mutated by replenishment; backlog membership remains the duplicate guard.

Expected score: 8.45. Observed score: 9.00. Calibration error: 0.55. Twelve-outcome calibration MAE: 0.88.

Against the frozen `+0.94` baseline, `exp-012` is the second true holdout: raw error 0.55 becomes 0.39. Across both holdouts the raw MAE is 0.55 and corrected MAE is 0.39, still a 29.09% improvement without refitting. The baseline remains frozen, and the new registry has replenished three pending experiments for the next autonomous cycles.

## 2026-09-13 — exp-016 completed

Implemented Elaine Mission Radar as the first Lumen capability aimed explicitly at helping the user choose what to do next rather than only improving the lab itself. `state/missions.json` keeps a small reviewed portfolio with a reason each mission matters now, one concrete next action, and bounded impact, urgency, leverage, momentum, effort, and risk scores. `lumen-radar` ranks active missions deterministically, supports top-N and JSON output, ignores paused/done missions, and never mutates or executes the recommendation.

The initial portfolio covers career leverage, Lumen itself, RobotCI, and the Elaine live-avatar project. The current top mission is career leverage: turn one real production LLM project into a concise portfolio case with architecture, metrics, failure modes, and trade-offs. This is intentionally a decision aid rather than an autonomous external actor; no network, model, secret, account action, or external execution is required.

Expected score: 8.70. Observed score: 9.30. Calibration error: 0.60. Thirteen-outcome calibration MAE: 0.85.

Against the frozen `+0.94` baseline, `exp-016` is the third true holdout: raw error 0.60 becomes 0.34. Across the three holdouts the raw MAE is 0.57 and corrected MAE is 0.37, a 35.09% improvement without refitting. The main product learning is that Lumen now has a clean boundary between its internal experiment backlog and a user-facing mission portfolio, so future features can help the user without turning personal goals into autonomous executable actions.

## 2026-09-13 — exp-017 completed

Implemented `lumen-work` so the Mission Radar recommendation becomes a bounded, executable-by-the-user session instead of ending at a sentence. Reviewed templates in `state/work_sessions.json` provide a focus window, ordered steps, and a Definition of Done for each current mission. The default selection reuses Mission Radar ranking, while `--mission` allows an explicit active-mission override and `--json` exposes the same session deterministically for integrations.

The default command is read-only. Progress changes require an explicit `--done <step-number>` and are written only to ignored `.lumen/work_progress.json`; mission definitions and templates are never rewritten. Lumen still does not execute the listed task, call a model, use secrets, or perform network/account actions. CI passed on Python 3.11, 3.12, and 3.13 after fixing the initial lint-only failure.

Expected score: 8.45. Observed score: 9.00. Calibration error: 0.55. Fourteen-outcome calibration MAE: 0.83.

Against the frozen `+0.94` baseline, `exp-017` is the fourth true holdout: raw error 0.55 becomes 0.39. Across four holdouts the raw MAE is 0.56 and corrected MAE is 0.38, a 32.89% improvement without refitting. The product learning is that mission selection and work execution can stay cleanly separated: Elaine can decide what deserves focus, structure the session, and track local progress without silently acquiring authority to perform external actions.
