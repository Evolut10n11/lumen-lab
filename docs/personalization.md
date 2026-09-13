# Per-user personalization

Lumen separates repository-owned laboratory evidence from machine-local user state.

## Why this exists

`state/` is part of the repository history. It contains the experiments, calibration evidence, mission examples, and other artifacts produced while developing Lumen itself. It must not silently become the personality or goal set of every person who installs Lumen.

Interactive user behavior therefore resolves through an explicit local identity and an isolated workspace under:

```text
.lumen/users/<user-id>/
```

`.lumen/` is ignored by Git, so personal goals, interests, progress, proposal backlogs, and journals are not committed by default.

## Identity resolution

Interactive commands resolve a user in this order:

1. `--user <id>` when supplied;
2. the `LUMEN_USER_ID` environment variable;
3. the local id `default`.

User ids are validated and cannot contain path separators or traversal sequences.

A user workspace must be initialized before normal `lumen-radar`, `lumen-work`, or user-scoped `lumen-propose` behavior can use it. Lumen does not fall back to `state/profile.json` when a local user has not been initialized.

## Onboarding

Create a local profile with explicit inputs:

```bash
lumen-user --user alex init \
  --name "Alex" \
  --priority career=10 \
  --priority health=7 \
  --interest robotics \
  --skill Python \
  --constraint "5 hours per week"
```

On Windows PowerShell the same command can be entered on one line:

```powershell
lumen-user --user alex init --name "Alex" --priority career=10 --priority health=7 --interest robotics --skill Python --constraint "5 hours per week"
```

Initialization creates a profile, a small starter mission portfolio, and matching focused-work templates from that user's own inputs. No hidden ChatGPT conversation context, repository-owner profile, model call, or network request is used for this bootstrap.

## State layout

A typical user workspace contains:

```text
.lumen/users/alex/
├── profile.json
├── missions.json
├── work_sessions.json
├── work_progress.json   # appears after progress is recorded
├── backlog.json         # appears when proposal/backlog flows are used
├── outcomes.json        # appears when outcome flows are used
└── journal.md           # appears when lab-store flows are used
```

Work progress is isolated by user, so two people using the same checkout cannot complete each other's steps.

## Compatibility and developer mode

Core parsers still accept explicit file paths for deterministic tests and repository maintenance. `lumen-propose --root <path>` without `--user` intentionally keeps the repository-owned developer-state mode. Normal interactive `lumen-propose` without an explicit `--root` uses the current local user workspace.

This split is deliberate: repository state is evidence about Lumen; user state is evidence about one person's goals and work.

## Application identity

A future desktop/web application should map its authenticated account or local installation id to the same internal `user_id`. The storage backend can later move from local JSON to a database without changing the rule that every profile, mission, session, proposal, feedback event, and outcome is scoped to exactly one user.
