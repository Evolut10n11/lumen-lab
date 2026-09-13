# Explicit profiles

Lumen personalization is driven by repository-owned data, not hidden chat history or a trained personal model.

`state/profile.json` is the default local profile. It can be replaced per user or project, or another file can be supplied to `lumen-radar --profile` and `lumen-work --profile`.

## Profile contract

A profile contains:

- `id` and `display_name` for explicit identity inside the local configuration;
- `priorities`: tag weights from 1 to 10;
- `skills`, `interests`, `constraints`, and `preferred_stack`: validated descriptive lists for current and future planning features;
- `risk_tolerance`: an integer from 1 to 10;
- `candidate_generation_policy`: an explicit policy describing whether future candidate generation is disabled, reviewed, or may optionally use an LLM.

The current Mission Radar only uses `priorities` and `risk_tolerance`. The other fields are stored now so future proposal generation has an explicit input contract instead of reading implicit user context.

## Mission alignment

Mission definitions may contain local `tags`. The original mission score remains unchanged and visible as `base_score`.

When a profile is present, Lumen computes an auditable adjustment:

1. find the highest profile priority matching any mission tag;
2. use neutral alignment `5` when no tag matches;
3. add `(alignment - 5) * 0.30` to the base score;
4. subtract `0.10` for each mission-risk point above the profile's risk tolerance;
5. clamp the final score to the 0..10 range.

This changes ranking without rewriting the mission or the base score. Stable mission-ID tie-breaking still applies.

## What the profile is not

The profile is not a memory dump, embedding store, behavioral dossier, or fine-tuned model. Lumen does not infer it from ChatGPT conversations. The checked-in example contains only deliberate, non-secret configuration and can be replaced completely.

No profile operation requires a network connection, model endpoint, account access, or secret.

## Future idea generation

`candidate_generation_policy` is intentionally policy-only in this experiment. An optional idea generator may later consume the explicit profile plus repository evidence, but generated candidates must still pass the normal Experiment schema, deterministic safety gates, and explicit backlog application flow. An LLM will not gain authority to execute a generated idea merely because it proposed it.
