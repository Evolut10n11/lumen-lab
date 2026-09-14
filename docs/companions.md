# Companion event contract

Lumen's companion layer reacts to committed product state. It does not choose missions, change scores, or decide whether work is complete.

Each user has an optional `.lumen/users/<user-id>/companion.json` file. The file stores the selected character, cumulative XP, the current direction chapter, processed event IDs, and the last reaction kind. Writes use the same atomic JSON path as other user state. A damaged companion file is quarantined without resetting the user's profile, missions, or progress.

The dashboard synchronizes companion events from validated progress:

- a newly observed completed step awards 5 XP;
- a newly observed completed mission awards 25 XP in addition to its step XP;
- deterministic event IDs make repeated dashboard reads and repeated step clicks idempotent;
- an explicit direction revision starts a new chapter, so rebuilt work can earn XP while cumulative XP remains intact.

The first included characters are Lumi, Kiro, and Momo. All three have `access: free`, localized names and dialogue, distinct personalities, and a visual accent. Switching characters never moves or resets XP. There is no purchase or entitlement path in this version.

The React shell renders the selected companion, its latest line, level progress, and a three-character picker. A later animation renderer can consume the same `last_reaction.kind` values (`greeting`, `step_completed`, and `mission_completed`) without coupling animation code to mission logic.
