# Localization contract

Lumen Desktop currently supports `en` and `ru` as first-class product locales. The desktop request locale is explicit input to the Python application layer; locale selection does not depend on a model, a network call, or hidden conversation context.

## Locale precedence

The locale selected in the desktop application is authoritative for the next bootstrap request. A stale locale stored in conversational onboarding context must not override that explicit desktop choice on restart. Successful bootstrap responses report the effective locale through the dashboard, and the desktop persists that value locally.

Conversational onboarding context also stores the last successfully applied explicit locale. This keeps the local workspace coherent across launches without making onboarding context the source of truth over a new user choice.

## Re-localizing generated work

Changing locale after onboarding re-localizes only deterministic starter content created by Lumen:

- starter mission titles and rationales;
- starter focus-session steps;
- starter definitions of done.

The operation preserves stable mission IDs and mission status. Existing work progress is stored separately and is not rewritten, so completed steps survive language changes. Existing focus-minute choices are preserved as well.

Lumen does not rewrite unrelated missions, GitHub-derived missions, feedback signals, or other user-owned state during locale synchronization.

If the current starter portfolio no longer matches the shape that Lumen can regenerate safely, synchronization fails closed instead of guessing how to rewrite user state.

## Regression coverage

`tests/test_locale_switching.py` verifies that an English workspace can switch to Russian and back while preserving mission IDs, completed-step progress, and focus minutes. It also pins the desktop bootstrap precedence so an explicit locale cannot be silently replaced by stale onboarding state.
