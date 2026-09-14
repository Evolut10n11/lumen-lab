# Lumen 0.2.1

Lumen 0.2.1 repairs Russian text that an older Windows build may already have saved with the wrong code page.

## What changed

- Existing profiles, onboarding answers, missions, work sessions, and other local JSON state are checked automatically during startup.
- High-confidence UTF-8/Windows-1251 and UTF-8/Latin-1 mojibake is restored without repeating onboarding or deleting application data.
- Each changed source file is retained locally with a `.before-encoding-repair` suffix before the repaired JSON is written atomically.
- Correct Russian and Western text remains unchanged, and the repair is idempotent across future launches.

## Compatibility

This patch keeps dashboard schema version 5 and all v0.2.0 user-state formats. It changes no account, payment, entitlement, telemetry, or companion XP behavior.
