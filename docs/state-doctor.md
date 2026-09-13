# State integrity doctor

`lumen-doctor` is a read-only consistency checker for the repository-owned Lumen state.
It is intended to run before autonomous work relies on persisted evidence.

## What it checks

The doctor reports deterministic `PASS` / `FAIL` checks in a stable order:

1. `backlog` — `state/backlog.json` is a valid list of experiments with unique IDs.
2. `outcomes` — `state/outcomes.json` is a valid list of outcomes with unique experiment IDs.
3. `experiment-outcome-links` — every outcome points to an existing `done` experiment, and every `done` experiment has exactly one outcome.
4. `candidate-registry` — `state/candidates.json` passes the same registry validation used by backlog replenishment.
5. `calibration-baseline` — the frozen baseline schema is valid and every training ID exists in the outcome ledger.
6. `holdout-evaluation` — the frozen holdout partition can be evaluated without changing or refitting the baseline.
7. `synthesis` — `state/SYNTHESIS.md` exactly matches a fresh deterministic in-memory render from backlog, outcomes, and journal text.

A healthy repository exits with status `0`. Any failed check produces a non-zero exit status and an actionable diagnostic.

## Usage

From the repository root:

```console
lumen-doctor
```

To inspect another checkout without changing the current directory:

```console
lumen-doctor --root /path/to/lumen-lab
```

## Safety boundary

The doctor never calls `LabStore.ensure()`, never creates missing files, never rewrites generated state, and never attempts a repair. Its job is detection only.

If `SYNTHESIS.md` is stale, regenerate it explicitly with `lumen-synthesize --write`. Other failed checks should be repaired deliberately at their source rather than hidden by an automatic fixer.

The doctor uses no model, network service, secret, or external statistics dependency.
