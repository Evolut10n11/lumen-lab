# Profile-driven proposal generation

`lumen-propose` turns an explicit local profile and repository-owned mission evidence into reviewable experiment proposals. Proposal generation is deliberately separated from execution and from persisted experiment state.

## Trust boundary

A proposal is not an experiment and has no execution authority. Generators cannot run commands, call tools, change external systems, or directly append to the backlog. The default command is preview-only.

The safe lifecycle is:

1. load and validate `state/profile.json`;
2. load repository missions and current experiments;
3. generate deterministic proposals, optionally enriched by an explicitly configured LLM adapter;
4. inspect proposals in human or JSON form;
5. explicitly write a review snapshot if a proposal should be considered for acceptance;
6. explicitly accept one proposal from that snapshot with a new normal experiment ID;
7. revalidate evidence, risk, duplicates, and the normal `Experiment` schema before changing the backlog.

There is intentionally no command that asks an LLM for proposals and accepts its fresh response in the same step.

## Profile policy

`candidate_generation_policy` controls proposal behavior:

- `disabled`: no proposals are produced;
- `reviewed`: only the deterministic baseline runs;
- `optional-llm`: deterministic proposals remain the baseline and an LLM adapter may enrich them only when `allow_llm` is true.

`max_candidates` caps the final batch. A proposal whose risk exceeds `risk_tolerance` is rejected.

## Deterministic baseline

The baseline ranks active missions with the same profile-aware ranking used by Mission Radar. Each accepted mission signal becomes a bounded proposal with explicit profile and mission evidence references. Existing experiment IDs and normalized titles are excluded.

This path is local, deterministic, requires no model or secret, and is suitable for CI tests.

## Optional LLM enrichment

An OpenAI-compatible adapter can be configured with `--endpoint` and `--model`. An optional bearer token is read from the environment variable named by `--token-env` (default `LUMEN_LLM_TOKEN`).

Model output must match the strict proposal schema, stay within the profile risk tolerance, and reference only evidence IDs that Lumen supplied. Malformed responses, unknown evidence, timeouts, and transport errors fail safely back to deterministic proposals. CI uses injected transports and never requires a live model endpoint.

## Commands

Preview without writes:

```console
lumen-propose
lumen-propose --json
```

Explicitly save the current batch for review:

```console
lumen-propose --write-review .lumen/proposals.json
```

Accept exactly one reviewed proposal as a normal backlog experiment:

```console
lumen-propose \
  --accept-file .lumen/proposals.json \
  --accept mission-robotci \
  --experiment-id exp-020
```

Acceptance revalidates the proposal against the current profile, missions, experiment IDs, titles, evidence references, risk tolerance, and normal experiment schema. Only `state/backlog.json` is changed by that operation.

Optional LLM enrichment:

```console
lumen-propose \
  --endpoint http://localhost:8000/v1/chat/completions \
  --model local-model
```

This only has an effect when the active profile explicitly uses `optional-llm` with `allow_llm: true`.

## Evidence references

Current evidence references are intentionally small and explicit:

- `profile:<profile-id>`
- `profile:priority:<tag>`
- `mission:<mission-id>`
- `experiment:<experiment-id>`

Unknown references invalidate a proposal. This keeps generated rationale traceable without pretending that free-form model text is evidence.

## Non-goals

This layer does not autonomously execute accepted experiments, does not modify GitHub, does not infer hidden user facts, and does not read ChatGPT memory. Future generators may gain richer evidence inputs, but the review and validation boundary should remain independent of the generator implementation.
