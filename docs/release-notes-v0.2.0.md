# Lumen 0.2.0

Lumen 0.2.0 turns the desktop prototype into a complete local progress loop.

## What changed

- Completing every step now closes the mission and advances the dashboard to the next active mission.
- Local JSON writes are atomic, and damaged optional user state is quarantined without losing the profile or healthy mission data.
- Desktop engine calls run away from the Tauri UI thread, drain both output streams, and stop with a useful error after 45 seconds.
- The Windows workflow installs the NSIS bundle and verifies that the installed `lumen-desktop.exe` stays running during startup.
- **Not now** moves a mission into a visible saved-for-later list. A paused mission can be restored from Activity.
- The Profile screen can revise the user's direction and rebuild current missions while preserving durable profile and connected GitHub evidence.
- Lumi, Kiro, and Momo are included as free local companions. Completed steps and missions award idempotent XP that remains with the user when they switch characters or revise direction.

## Compatibility

The desktop dashboard payload is schema version 5. Existing profile, mission, progress, feedback, onboarding, and GitHub context files remain supported. Companion state is optional and created on first companion change or earned XP event.

This release keeps all companion and progress data on the user's machine. It adds no account, payment, entitlement, or telemetry path.
