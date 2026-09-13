# Experiment provenance

`lumen-provenance` provides a deterministic, local evidence index for completed experiments.

The explicit artifact registry lives in `state/provenance.json`. Each completed experiment has exactly one record with one or more repository-relative artifact paths. The registry is intentionally small and auditable; it does not inspect Git history, call GitHub, use a model, or infer evidence from conversation context.

For each record the command joins three local sources:

- the completed experiment title from `state/backlog.json`;
- the recorded result from `state/outcomes.json`;
- whether `state/journal.md` contains an experiment section;
- the explicit evidence artifacts from `state/provenance.json`.

The artifact list is the only explicit provenance mapping. Outcome text and journal presence are supporting context, not replacements for the registry.

## Usage

```bash
lumen-provenance
lumen-provenance --experiment exp-013
lumen-provenance --json
```

The command is read-only. It validates that every completed experiment has an outcome and provenance record, rejects unknown/non-completed IDs, duplicate IDs and artifact paths, absolute paths, parent traversal, Windows-style separators, and missing artifact files.

`lumen-doctor` runs the same provenance validation as part of repository health checks. Neither command repairs state automatically.

## Maintenance rule

When an experiment is completed, add its provenance record in the same change that records the outcome. Prefer a compact set of primary implementation, test, state, or documentation artifacts rather than listing every touched file.
