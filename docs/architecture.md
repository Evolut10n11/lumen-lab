# Architecture

## Goal

Lumen Lab is an auditable loop for self-directed engineering experiments. Its architecture intentionally separates decision state from execution so that every autonomous step can be inspected, reproduced, or overridden.

## Core loop

```text
idea -> backlog -> deterministic scoring -> active experiment -> implementation -> result -> journal -> new evidence
```

### Experiment model

Each experiment contains a hypothesis and five 1..10 signals: impact, learning value, feasibility, novelty, and risk. The initial deterministic score is:

```text
0.35 * impact
+ 0.30 * learning
+ 0.20 * feasibility
+ 0.15 * novelty
- 0.25 * risk
```

This is deliberately understandable rather than "smart". Future planners may propose or adjust scores, but the stored inputs and final decision must remain inspectable.

### State

`state/backlog.json` is the source of truth for experiment lifecycle state. `state/journal.md` records decisions and observations. Generated snapshots such as `state/PULSE.md` are derived artifacts.

### Safety boundary

The default core does not execute arbitrary shell commands, access secrets, modify external systems, or call paid APIs. Any capability with meaningful side effects must be introduced as an explicit adapter with its own contract and tests.

### Autonomous development

Repository work should follow small increments with tests. GitHub Issues can later become the human-visible control plane, while the internal backlog remains portable and runnable without GitHub.

## Evolution path

1. Bootstrap deterministic planner and persistence.
2. Add an experiment outcome ledger and calibration metrics.
3. Synchronize selected experiments with GitHub Issues.
4. Add optional provider-neutral LLM proposal generation.
5. Add a constrained execution sandbox for explicitly approved experiment types.
6. Use accumulated outcomes to calibrate prioritization weights.
