# Per-user personalization

Lumen keeps repository-owned laboratory evidence separate from the person actually using the product.

## The important part for users

A new user should not have to tune Lumen like a control panel.

The product starts from a small amount of explicit information, then adapts from real use:

- what the user starts and completes;
- what they ask to see more often;
- what they postpone;
- what they explicitly want less of.

The internal ranking remains deterministic and inspectable, but the primary product surface uses normal product actions instead of sliders and manual score editing.

## User isolation

Every user has a separate local workspace:

```text
.lumen/users/<user-id>/
```

`.lumen/` is ignored by Git, so personal goals, progress, preferences, and learned signals are not committed by default.

Lumen never falls back to the repository owner's profile or work history for a different user.

## Lightweight onboarding

Only a small starting signal is required. For example:

```powershell
lumen-user --user alex init --name "Alex" --priority career=10
```

Interests, skills, constraints, preferred stack, and risk tolerance can enrich the first recommendations, but they do not need to become a long setup wizard in the GUI.

The product can collect more context later, when it is actually useful.

## Learning from use

A user's learned preference state lives in:

```text
.lumen/users/<user-id>/feedback.json
```

The GUI exposes three simple steering actions:

- `more_like_this` — positive signal for the mission and its kind of work;
- `not_now` — downrank only the current mission;
- `less_like_this` — negative signal for the mission and its kind of work.

Completing an entire work session also records one positive signal automatically. Re-opening or re-completing the finished session does not create duplicate learning events.

This means personalization improves even if the user never opens a settings screen.

## Revising direction

Behavioral learning should not trap a user inside their first onboarding answer. Sometimes the correct signal is not “less like this”; the person has explicitly changed direction.

The desktop engine therefore supports an explicit `revise_direction` action. It accepts a new desired change and can optionally update the user's current context, friction, and realistic focus window.

A direction revision is treated as stronger evidence than inferred behavior:

```text
explicit new direction
→ replace the primary priority
→ update matching context hypotheses
→ rebuild current personalized missions
→ reset progress tied to the old current mission set
→ preserve long-lived feedback and optional integrations
→ rebuild GitHub-derived work against the new goal when GitHub is connected
```

The revision is also appended to context history with its previous and new primary goal. This gives the product an auditable explanation for why recommendations changed instead of silently rewriting the user's history.

When current context or friction is explicitly revised, their corresponding onboarding-derived interest or constraint is updated at the same time. The profile and hypothesis model therefore cannot drift into two contradictory versions of the user.

This engine capability is intentionally separate from presentation. A desktop conversation, profile action, or future clarification flow can call the same operation without duplicating personalization logic in the GUI.

## State layout

A typical mature workspace can contain:

```text
.lumen/users/alex/
├── profile.json
├── missions.json
├── work_sessions.json
├── work_progress.json
├── feedback.json
├── backlog.json
├── outcomes.json
└── journal.md
```

Only files that are actually needed are created.

## Why feedback is split into mission and topic signals

`Not now` should not mean `I dislike this topic`.

For that reason, Lumen distinguishes between feedback about one concrete mission and feedback that can generalize through mission tags. This keeps temporary timing decisions from poisoning future recommendations.

## Developer mode

Core parsers still accept explicit file paths for deterministic tests and repository maintenance. Repository-owned `state/` remains evidence about Lumen itself; user-owned `.lumen/` state remains evidence about one person's goals and behavior.

## Application identity

A desktop or web client should map its authenticated account or local installation id to the same internal `user_id`. The storage backend can later move from local JSON to a database without changing the rule that every profile, mission, session, proposal, feedback event, and outcome belongs to exactly one user.
