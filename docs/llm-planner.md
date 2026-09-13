# Optional LLM planner adapter

Lumen Lab remains deterministic by default. `lumen advise` without an endpoint uses the existing score-based planner and performs no network requests.

## Optional OpenAI-compatible endpoint

The adapter accepts a full chat-completions endpoint and a model name. It uses only the Python standard library, so the base package gains no provider SDK dependency.

Example with a local OpenAI-compatible server:

```bash
lumen advise \
  --endpoint http://127.0.0.1:11434/v1/chat/completions \
  --model qwen3
```

An API token is optional. This lets local servers work without secrets. For remote providers, pass `--token` or set `LUMEN_LLM_TOKEN`.

```bash
export LUMEN_LLM_TOKEN='token-from-your-provider'
lumen advise \
  --endpoint https://provider.example/v1/chat/completions \
  --model provider-model
```

## Safety model

The LLM is advisory, not authoritative:

- it can select only an experiment ID that already exists in the current `backlog`;
- it cannot create experiments, change status, edit files, or execute commands;
- malformed JSON, invented IDs, timeout/network failures, and invalid responses fall back to the deterministic planner;
- no endpoint means no network traffic;
- the token is never required for local/offline endpoints and is sent only as a Bearer header when explicitly supplied;
- `lumen next` remains deterministic. LLM advice does not silently mutate planning state.

The adapter intentionally asks for a small JSON object containing `experiment_id` and `reason`. Even a syntactically valid recommendation is rejected when its ID is not an eligible backlog item.

## Why the deterministic planner stays primary

LLM recommendations are useful for qualitative trade-offs that the fixed score does not encode, but they are less predictable and may depend on provider behavior. Lumen therefore treats them as optional evidence. The deterministic score remains the reproducible baseline and the automatic fallback.
