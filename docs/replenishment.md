# Backlog replenishment

`lumen replenish` exists for the moment when every current experiment is finished or dropped and the autonomous loop would otherwise have no next action.

The mechanism is intentionally conservative. It does not ask a model to invent arbitrary work and it does not call external services. Instead, the repository contains a small curated second-generation candidate set in `src/lumen_lab/replenishment.py`.

## Safety policy

Replenishment follows five rules:

1. It is local and deterministic. No network access, credentials, or model endpoint is involved.
2. It refuses to propose anything while an experiment is still `backlog` or `active`.
3. Candidate IDs are stable. Existing IDs are never overwritten or duplicated, even if the existing item is already done or dropped.
4. Every candidate is reconstructed through the normal `Experiment` schema and validated before it can be returned or persisted.
5. The CLI is dry-run by default. State changes require an explicit `lumen replenish --apply`.

Dry run:

```bash
lumen replenish
```

Apply the validated candidates:

```bash
lumen replenish --apply
```

Applying replenishment appends only the new candidates to `state/backlog.json` and records the addition in the journal.

## Why not free-form generation yet?

The lab currently has only a small outcome history. Free-form model generation would add a second source of uncertainty before the planner itself has enough calibration evidence. Curated replenishment keeps the next cycle auditable while still allowing the project to escape an empty backlog.

A later experiment can evaluate broader idea generation once there is enough evidence to measure whether it improves learning or merely increases novelty and risk.
