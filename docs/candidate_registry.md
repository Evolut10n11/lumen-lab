# Declarative candidate registry

Future curated experiments live in `state/candidates.json`. The registry is repository-owned input, not generated state and not a second backlog.

Each entry uses the normal `Experiment` schema and must have `status: "backlog"`. Loading rejects malformed JSON shapes, invalid experiment values, non-backlog statuses, and duplicate IDs before any backlog mutation can happen.

`lumen replenish` keeps its existing operating boundary:

- pending `backlog` or `active` work blocks replenishment;
- dry-run is the default;
- `--apply` is required to append candidates to `state/backlog.json`;
- candidates already present in the backlog are filtered without modifying the registry;
- remaining candidates are ordered by the normal deterministic planner score with the existing stable ID tie-break;
- applying candidates does not delete or mark registry entries as consumed. Their presence in `state/backlog.json` is the durable duplicate guard.

The registry deliberately contains no code, commands, model prompts, network endpoints, or secrets. Adding a future experiment is a reviewable data change. It still requires the normal Issue/branch/PR/CI experiment workflow before implementation.

The historical `exp-006`, `exp-007`, and `exp-008` templates remain in the registry for provenance; because their IDs already exist in the backlog they are never proposed again. New curated entries can be added without editing `replenishment.py`.
