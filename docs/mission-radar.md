# Elaine Mission Radar

Mission Radar is the first Lumen capability aimed directly at the user rather than at the lab itself. It answers one question: **where should Elaine and the user invest the next focused block of effort?**

The source of truth is `state/missions.json`. Each mission contains a short reason it matters now, one concrete next action, and six integer scores from 1 to 10:

- `impact` — upside if the mission succeeds;
- `urgency` — cost of delaying it;
- `leverage` — how much future work or opportunity it unlocks;
- `momentum` — how much useful progress already exists;
- `effort` — cost of the next meaningful increment;
- `risk` — downside or uncertainty.

The deterministic score is:

```text
0.30*impact + 0.20*urgency + 0.25*leverage + 0.15*momentum
+ 0.10*(11-effort) - 0.15*risk
```

Only missions with `status: "active"` are ranked. Equal scores are ordered by mission ID, so output is stable across runs.

## Usage

```bash
lumen-radar
lumen-radar --top 3
lumen-radar --json
```

The command is read-only. It does not execute the recommended action, edit the mission file, call a model, access the network, or use secrets.

## Updating priorities

Edit `state/missions.json` in a normal reviewed change. Prefer changing a score only when the real situation changed, and keep `next_action` small enough to finish or decisively test in one focused work block.

Use `paused` when a mission is valid but should not compete for attention. Use `done` when its current objective is complete. Do not inflate scores just to force ordering; if two missions feel mis-ranked, first inspect which dimension is actually wrong.

Mission Radar is a decision aid, not an autonomous executor. External actions remain separate and require the normal safety and approval boundaries of the environment in which Lumen is running.
