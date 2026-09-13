# State schema versioning

Lumen keeps persisted JSON state intentionally simple, but silent format drift becomes risky as more commands depend on the same files. `state/schema_versions.json` is the repository-owned compatibility contract for those JSON files.

The manifest has its own `manifest_version` and an exact mapping from managed state file names to schema versions. Validation is strict: missing managed files, unknown file names, malformed versions, unsupported future manifest versions, and unsupported per-file versions are errors.

## Inspect

```bash
lumen-schema
lumen-schema --json
```

Inspection is read-only. A current repository reports `current` and requires no migration.

## Legacy migration

A repository created before schema metadata existed is treated as `legacy-unversioned` only when the manifest is absent. Previewing that state never writes anything:

```bash
lumen-schema
```

Migration is explicit:

```bash
lumen-schema --migrate
```

The current migration creates only `state/schema_versions.json` after verifying that every managed payload file exists. It does not rewrite backlog, outcomes, profile, mission, provenance, capability, candidate, calibration, or work-session payloads. If the manifest already exists, validation runs instead of silently replacing it.

Future payload migrations should be added as deterministic version-to-version transforms with tests before a supported version number changes. A schema-version bump should update the supported-version code, manifest, migration tests, and migration documentation together in one reviewed change. Unknown future versions fail closed rather than being guessed.

## Doctor integration

`lumen-doctor` validates the schema manifest before relying on repository state. Schema drift therefore becomes a visible health failure instead of an implicit compatibility assumption.

## Trust boundary

Schema migration is local filesystem state maintenance. It does not use the network, models, secrets, shell commands, GitHub writes, or external services. The current migration is deliberately metadata-only and reversible by removing the generated manifest in an uncommitted legacy checkout.
