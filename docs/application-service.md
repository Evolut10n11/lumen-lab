# Application service

`LumenApplication` is the product-facing boundary between Lumen's domain logic and the GUI.

The GUI should feel like a product, not a settings panel. A user should be able to open Lumen, see one useful next move, act on it, and let the system adapt in the background.

## Product principle

The default experience is **use first, tune never**.

A user does not need to understand ranking weights, feedback scores, state files, or mission formulas. Those remain inspectable for developers, but the product surface exposes only simple choices:

- **Start / Continue** — work on the current recommendation;
- **More like this** — increase preference for this kind of work;
- **Not now** — downrank only this item without teaching Lumen that the whole topic is bad;
- **Less like this** — reduce preference for this kind of work.

Completing a full session is also treated as a positive preference signal automatically. No extra rating prompt is required.

## User boundary

Every call is resolved through `UserWorkspace` and reads or writes only the selected user's local workspace under:

```text
.lumen/users/<user-id>/
```

Feedback and learned preference signals are stored in the same user boundary. One person's behavior cannot influence another person's ranking.

## Bootstrap

A GUI starts with one call:

```python
payload = app.bootstrap("alice")
```

If the user is new, render onboarding. If the user already exists, render the returned dashboard. The GUI never needs to inspect `.lumen/` directly.

## Dashboard as a product contract

```python
payload = app.dashboard("alice")
```

The payload contains both domain data and an `experience` block intended for direct UI rendering.

The important product-facing fields are:

```text
experience.headline
experience.message
experience.primary_action
experience.quick_actions
experience.learning
```

A client can therefore render a useful home screen without recreating recommendation wording or exposing tuning controls.

The lower-level `today`, `radar`, and selection explanation remain available for expandable detail views and debugging.

## Lightweight reactions

The GUI should send action ids rather than asking the user to edit weights:

```python
app.react_to_mission("more_like_this", "alice")
app.react_to_mission("not_now", "alice")
app.react_to_mission("less_like_this", "alice")
```

`not_now` affects only the current mission. `more_like_this` and `less_like_this` can generalize through mission tags so future ranking becomes more personal.

## Passive learning

```python
app.complete_step(1, "alice")
```

Normal progress remains normal progress. When a user completes the final step of a session for the first time, Lumen records one positive preference signal automatically.

Repeatedly opening or re-completing an already finished step does not create duplicate preference events.

This gives Lumen useful adaptation even when a user never presses a feedback button.

## Onboarding

`onboard()` still accepts explicit profile inputs, but the GUI should keep the first-run experience small. It can begin from a name and a small number of high-level goals, then let actual usage refine ranking over time.

```python
app.onboard(
    "alice",
    display_name="Alice",
    priorities={"career": 10},
)
```

Additional interests, skills, constraints, stack preferences, and risk tolerance are optional enrichment rather than a required configuration wizard.

## Design rule for the GUI

The home screen should answer three questions immediately:

1. What is the best next thing for me right now?
2. What happens when I press the main button?
3. How do I gently steer Lumen if the recommendation is wrong?

Everything else belongs behind progressive disclosure. Raw scores and internal state are for explainability and debugging, not the primary product surface.
