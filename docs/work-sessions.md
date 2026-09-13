# Elaine focused work sessions

`lumen-work` turns Mission Radar's current top active mission into a concrete bounded work session.

## Inputs

Curated session templates live in `state/work_sessions.json`. Each template is keyed by a mission ID and contains:

- a focus window in minutes;
- an ordered list of executable steps;
- a Definition of Done.

Templates are validated before use. Duplicate mission IDs, malformed steps, empty text, and unreasonable focus windows are rejected.

The mission itself still comes from `state/missions.json`, and the default selection uses the same deterministic ranking as `lumen-radar`. `--mission <id>` can select another active mission explicitly.

## Progress

Running `lumen-work` without `--done` is read-only. It does not create files.

`lumen-work --done N` marks step `N` complete for the selected mission. This writes only to `.lumen/work_progress.json`, which is intentionally ignored by Git. The curated mission portfolio and reviewed session templates remain unchanged.

Progress updates are idempotent: marking the same step twice does not duplicate it. Invalid step numbers are rejected.

## Examples

```bash
lumen-work
lumen-work --done 1
lumen-work --done 2
lumen-work --mission robotci
lumen-work --json
```

The default human-readable output includes the mission, reason it matters now, priority score, focus window, progress, checklist, and Definition of Done.

## Safety boundary

A work session is a planning and progress-tracking surface, not an executor. It does not call a model, use the network, read secrets, open accounts, run commands, edit other repositories, or perform the listed work automatically.

The only mutation available through this command is an explicit `--done` progress update to ignored local runtime state. This keeps user intent visible and prevents a planning recommendation from silently becoming an external action.
