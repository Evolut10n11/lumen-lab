# Lumen Lab

Lumen Lab is a self-directed software R&D laboratory maintained by ChatGPT inside this repository.

The goal is not to build one fixed product. The repository is an evolving environment where ideas become experiments, experiments become reusable tools, and every important decision is recorded.

## Operating model

1. Ideas enter the backlog with a hypothesis and an expected value.
2. The planner scores them by impact, learning value, feasibility, novelty, and risk.
3. The highest-value safe experiment becomes the next focus.
4. Work is implemented in small, testable increments.
5. Results are written to the lab journal and feed the next planning cycle.

## First milestone

The first version is intentionally local and dependency-light: a Python CLI that can seed ideas, rank the backlog, select the next experiment, complete work, and append journal entries. GitHub Actions keeps the core healthy.

Later milestones may add optional LLM planning, GitHub Issues synchronization, experiment sandboxes, benchmark tracking, and autonomous scheduled pulses.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .[dev]
lumen seed
lumen status
lumen next
pytest
```

## Principles

- Prefer useful artifacts over demos.
- Keep every autonomous action auditable.
- Never require secrets for the default path.
- Make risky or irreversible behavior opt-in.
- Small experiments are better than speculative rewrites.
- Tests and a readable journal are part of the product.

## Repository map

- `src/lumen_lab/` — core engine and CLI.
- `state/` — backlog and journal data.
- `tests/` — executable behavior contracts.
- `.github/workflows/` — CI and scheduled health checks.
- `docs/` — architecture and operating notes.

The project starts small on purpose. Its scope is allowed to evolve as the lab learns.