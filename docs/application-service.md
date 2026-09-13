# Application service

`LumenApplication` is the application-facing boundary between Lumen's domain logic and any client UI.

The goal is to keep a future desktop or web interface thin. The UI should not reimplement mission ranking, user scoping, progress updates, or explanation logic. It should call this service and render the returned payloads.

## User boundary

Every call is resolved through `UserWorkspace` and therefore reads or writes only the selected user's local workspace under:

```text
.lumen/users/<user-id>/
```

If `user_id` is omitted, the same default-user resolution used by the CLI applies (`LUMEN_USER_ID`, then `default`).

## Dashboard

```python
from pathlib import Path
from lumen_lab.app_service import LumenApplication

app = LumenApplication(Path.cwd())
payload = app.dashboard("alice")
```

The dashboard payload contains:

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

The same service is available through:

```text
lumen-dashboard --user alice
lumen-dashboard --user alice --json
lumen-dashboard --user alice --done 1 --json
```

The JSON mode is useful as a temporary integration surface while the GUI is being built. A future HTTP or desktop adapter should call `LumenApplication` directly instead of shelling out to the CLI.

## Design rule for the GUI

The application client should remain presentation-focused:

1. onboarding creates a user profile and workspace;
2. the home screen renders `dashboard()`;
3. completing a step calls `complete_step()`;
4. the UI renders the returned explanation rather than inventing its own ranking rationale.

This keeps one source of truth for personalization across CLI, tests, and future GUI clients.
