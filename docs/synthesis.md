# Journal synthesis snapshot

`lumen-synthesize` creates a disposable, deterministic view over the lab's accumulated evidence. The append-only journal remains the narrative source of truth; synthesis exists to make repeated operational lessons and pending capabilities easier to inspect.

## Usage

Preview without changing repository state:

```bash
lumen-synthesize
```

Write the generated view explicitly:

```bash
lumen-synthesize --write
```

The write mode replaces only `state/SYNTHESIS.md`. It never rewrites or truncates `state/journal.md`.

## Evidence and provenance

The snapshot reports:

- completed experiment IDs and count from `state/backlog.json`;
- recorded outcome count and calibration summary from `state/outcomes.json`;
- the number of level-two journal sections in `state/journal.md`;
- repeated lesson signals with the experiment IDs that support each signal;
- current missing capabilities as the deterministic ranked backlog.

A repeated lesson signal appears only when at least two distinct recorded outcome summaries match an explicit keyword rule. The current rules cover deterministic controls, safety boundaries, and tests/documentation. This threshold prevents a single experiment from being promoted into a project-wide lesson.

## Limits

The synthesis is intentionally not semantic analysis. Keyword matches can miss synonymous wording or match text whose meaning is more nuanced. For that reason, every signal includes supporting experiment IDs and the generated file describes itself as a view rather than an authority.

No LLM, network service, credential, or external repository is required. The synthesis must not invent new backlog work; pending capabilities come only from the existing validated backlog and use the normal planner ranking.
