# Application service

`LumenApplication` is the application-facing boundary between Lumen's domain logic and any client UI.

The goal is to keep a future desktop or web interface thin. The UI should not reimplement onboarding, mission ranking, user scoping, progress updates, or explanation logic. It should call this service and render the returned payloads.

## User boundary

Every call is resolved through `UserWorkspace` and therefore reads or writes only the selected user's local workspace under:

```text
.lumen/users/<user-id>/
```

If `user_id` is omitted, the same default-user resolution used by the CLI applies (`LUMEN_USER_ID`, then `default`).

## Bootstrap

A GUI can ask for one startup payload before it decides which screen to render:

```python
payload = app.bootstrap("alice")
```

The bootstrap payload contains:

- `schema_version`: the application contract version;
- `selected_user_id`: the user the app resolved for this launch;
- `initialized`: whether that user's workspace already exists;
- `users`: initialized local users available for profile switching;
- `dashboard`: the selected user's dashboard when initialized, otherwise `null`.

This gives the client a deterministic startup rule: render onboarding when `initialized` is false, otherwise render the main dashboard. The GUI never needs to inspect `.lumen/` directly.

## Onboarding

The app layer can create an isolated user directly from explicit inputs:

```python
from pathlib import Path
from lumen_lab.app_service import LumenApplication

app = LumenApplication(Path.cwd())
payload = app.onboard(
    "alice",
    display_name="Alice",
    priorities={"career": 10, "health": 7},
    interests=["robotics"],
    skills=["python"],
    constraints=["4 hours per week"],
    risk_tolerance=4,
)
```

`onboard()` creates the profile, starter missions, and work-session templates, then returns the user's first dashboard. Reusing an existing user id raises an error unless `replace=True` is passed explicitly. Replacement rebuilds that user's generated state and resets only that user's progress.

## Dashboard

```python
payload = app.dashboard("alice")
```

The dashboard payload contains:

- `schema_version`: the application contract version;
- `user`: explicit profile data for the selected user;
- `today`: the currently selected mission, work-session progress, and an explanation of why it was selected;
- `radar`: the ranked mission list;
- `summary`: active mission and progress totals.

The selection explanation exposes the personalized score, base score, matched priorities, and human-readable reasons. This is intended to make the product auditable rather than presenting recommendations as unexplained model output.

## Completing work

```python
app.complete_step(1, "alice")
```

Progress is written only to that user's workspace. Tests cover cross-user isolation.

## CLI bridge

The same dashboard service is available through:

```text
lumen-dashboard --user alice
lumen-dashboard --user alice --json
lumen-dashboard --user alice --done 1 --json
```

The JSON mode is useful as a temporary integration surface while the GUI is being built. A future HTTP or desktop adapter should call `LumenApplication` directly instead of shelling out to the CLI.

## Design rule for the GUI

The application client should remain presentation-focused:

1. app launch calls `bootstrap()`;
2. onboarding calls `onboard()` with explicit user inputs;
3. the home screen renders `dashboard()`;
4. completing a step calls `complete_step()`;
5. the UI renders the returned explanation rather than inventing its own ranking rationale.

This keeps one source of truth for personalization across CLI, tests, and future GUI clients.
