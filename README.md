# Lumen Lab

Lumen Lab is a self-directed software R&D laboratory maintained by ChatGPT inside this repository.

The goal is not to build one fixed product. The repository is an evolving environment where ideas become experiments, experiments become reusable tools, and every important decision is recorded.

## Operating model

1. Ideas enter the backlog with a hypothesis and an expected value.
2. The planner scores them by impact, learning value, feasibility, novelty, and risk.
3. The highest-value safe experiment becomes the next focus.
4. Work is implemented in small, testable increments.
5. Results are written to the lab journal and feed the next planning cycle.

## Current capabilities

The project is intentionally local and dependency-light. The Python CLI can rank and complete experiments, track calibration outcomes, mirror owned backlog items to GitHub Issues, request optional OpenAI-compatible planning advice with deterministic fallback, and run controlled subprocess experiments in a constrained temporary workspace.

The subprocess layer is deliberately described as process containment rather than a strong security sandbox. It uses explicit executable allowlists, no shell, a minimal environment, temporary working directories, timeout enforcement, bounded output capture, and structured results. See `docs/sandbox.md` for the threat model and limitations.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .[dev]
lumen status
lumen ledger
pytest
```

A controlled sandbox example:

```bash
lumen sandbox --allow python --timeout 2 --json -- python -c "print('hello')"
```

## Principles

- Prefer useful artifacts over demos.
- Keep every autonomous action auditable.
- Never require secrets for the default path.
- Make risky or irreversible behavior opt-in.
- Small experiments are better than speculative rewrites.
- Tests and a readable journal are part of the product.
- Do not claim stronger isolation than the operating system actually enforces.

## Repository map

- `src/lumen_lab/` — core engine and CLI.
- `state/` — backlog, experiment outcomes, and journal data.
- `tests/` — executable behavior contracts.
- `.github/workflows/` — CI and scheduled health checks.
- `docs/` — architecture, safety notes, and operating guidance.

The project starts small on purpose. Its scope is allowed to evolve as the lab learns.
