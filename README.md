# Lumen Lab

Lumen Lab is an auditable engine for turning a person's priorities into ranked missions, focused work sessions, reviewable experiments, and evidence for the next decision.

The repository also remains a self-directed R&D laboratory for improving Lumen itself. Those two concerns are intentionally separated: repository-owned `state/` describes the product's own experiment history, while each real person's goals and progress live in an isolated machine-local workspace under `.lumen/users/<user-id>/`.

That boundary matters. Installing Lumen must never make a new user inherit the repository owner's career goals, interests, missions, or work history.

## What Lumen does

For a user, the loop is:

1. Capture explicit priorities, interests, skills, constraints, preferred tools, and risk tolerance.
2. Build an isolated local profile and starter mission portfolio from those inputs.
3. Rank missions against that user's profile instead of a global persona.
4. Turn the best current mission into a bounded work session with a Definition of Done.
5. Record progress only inside that user's workspace.
6. Generate reviewable proposals from the same user-scoped evidence, with optional LLM enrichment only when the profile explicitly permits it.
7. Use outcomes as evidence for later prioritization instead of silently rewriting the user's goals.

The repository-development loop is separate and keeps its existing deterministic experiment planner, calibration ledger, provenance index, state doctor, constrained subprocess runner, schema versioning, and GitHub integration.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .[dev]
```

Create your own local profile instead of using repository-owned demo state:

```bash
lumen-user --user alex init \
  --name "Alex" \
  --priority career=10 \
  --priority health=7 \
  --interest robotics \
  --skill Python \
  --constraint "5 hours per week"
```

PowerShell users can run the same command on one line:

```powershell
lumen-user --user alex init --name "Alex" --priority career=10 --priority health=7 --interest robotics --skill Python --constraint "5 hours per week"
```

Then use the same identity for personalized commands:

```bash
lumen-radar --user alex --top 3
lumen-work --user alex
lumen-work --user alex --done 1
lumen-work --user alex --json
lumen-propose --user alex
```

Instead of repeating `--user`, set `LUMEN_USER_ID=alex` in your environment. If neither is set, interactive commands resolve the local id `default` and require that workspace to be initialized first.

## Personalization model

A user's state is local and Git-ignored:

```text
.lumen/users/alex/
├── profile.json
├── missions.json
├── work_sessions.json
├── work_progress.json
├── backlog.json
├── outcomes.json
└── journal.md
```

Only files that are actually used are created. Onboarding creates the profile, personalized missions, and matching work-session templates. Progress and proposal/lab files appear when those flows are used.

`lumen-user` never reads hidden ChatGPT memory or copies `state/profile.json`. Its deterministic bootstrap is derived only from the inputs supplied for that user. Optional model-backed proposal enrichment remains explicit and policy-gated.

See `docs/personalization.md` for identity resolution, storage rules, developer compatibility, and the application boundary.

## Mission Radar

`lumen-radar` ranks active missions using impact, urgency, leverage, momentum, effort, risk, and alignment with the selected user's weighted priorities. Two users can rank the same portfolio differently, and in normal interactive use they do not even share the same portfolio.

Use an explicit mission file only for tests or deliberate developer workflows:

```bash
lumen-radar --state path/to/missions.json --top 3
```

See `docs/mission-radar.md`.

## Focused work sessions

`lumen-work` selects the best active mission for the current user, loads its reviewed/generated template, and renders a bounded checklist plus Definition of Done. Reading a session is write-free. `--done <step>` writes progress only to that user's local workspace.

```bash
lumen-work --user alex
lumen-work --user alex --done 2
```

See `docs/work-sessions.md`.

## Reviewable proposals

`lumen-propose` turns the current profile and mission evidence into candidate experiments without automatically executing or accepting them. The default deterministic path requires no model or network. A profile may explicitly opt into OpenAI-compatible enrichment, and malformed or unavailable model output falls back safely.

Normal interactive use is user-scoped. Supplying `--root <path>` without `--user` intentionally retains the repository-owned developer-state mode used by lab maintenance and deterministic tests.

See `docs/proposals.md`.

## Repository laboratory

The original self-improvement laboratory remains available for developing Lumen itself:

```bash
lumen status
lumen ledger
lumen-doctor
lumen-provenance
lumen-schema
pytest
```

The laboratory uses repository-owned `state/` for auditable experiment evidence. Backlog ideas are scored by impact, learning, feasibility, novelty, and risk; outcomes feed calibration and holdout checks; provenance links completed experiments to artifacts; schema and doctor commands validate the stored evidence.

This repository state is not a default end-user persona.

## Safety and product principles

- A real user owns a separate state boundary; no cross-user profile or progress fallback.
- Personal state is ignored by Git by default.
- Prefer explicit evidence over hidden personalization.
- Optional model behavior must have deterministic validation and fallback.
- Risky or irreversible actions stay opt-in.
- Reading/ranking should not mutate state.
- Tests, provenance, and readable decision history are part of the product.
- Do not claim stronger sandboxing or autonomy than the underlying system actually provides.

## Repository map

- `src/lumen_lab/` — core engine and CLIs.
- `src/lumen_lab/workspace.py` — user identity and isolated local paths.
- `src/lumen_lab/personalization.py` — explicit-profile bootstrap into missions and work sessions.
- `state/` — repository-owned Lumen R&D evidence, not a universal user profile.
- `.lumen/users/` — ignored machine-local per-user state.
- `tests/` — executable behavior contracts, including cross-user isolation tests.
- `.github/workflows/` — CI and scheduled repository checks.
- `docs/` — architecture, trust boundaries, schemas, and operating guidance.

## Direction

The current interface is CLI-first so behavior remains easy to test and audit. The next product layer is an application UI built on the same `user_id -> profile -> missions -> work session -> feedback` boundary. Keeping that boundary in the core first prevents a polished interface from accidentally exposing one person's state to everyone else.
