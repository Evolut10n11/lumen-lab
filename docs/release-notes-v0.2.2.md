# Lumen 0.2.2

Lumen 0.2.2 completes the automatic recovery of Russian text saved by older Windows builds.

## What changed

- Short one-character Cyrillic words such as `Я` are restored when they appear inside otherwise-correct localized mission text.
- Pre-repair backups are copied to a temporary file and moved into place atomically. A partial backup left by v0.2.1 is detected against the still-pristine live source and safely replaced before repair.
- Existing recovery behavior for Windows-1251, Windows-1252, Latin-1, mixed localized strings, and colliding JSON keys remains covered.

## Compatibility

This patch keeps dashboard schema version 5 and all v0.2.x user-state formats. Installing it over v0.2.0 or v0.2.1 preserves the user's profile, missions, progress, feedback, companion, and XP.
