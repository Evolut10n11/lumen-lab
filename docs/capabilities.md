# Sandbox capability manifests

Capability manifests are named, reviewable configurations for the existing constrained subprocess runner. They reduce repeated command-line policy without adding a new execution mechanism.

## Repository policy

The default manifest document is `state/capabilities.json`. Each manifest contains:

- a stable lowercase name;
- one or more bare executable names;
- a timeout no greater than 60 seconds;
- an output limit no greater than 1,000,000 bytes;
- an optional human-readable description.

Every executable is validated by the same bare-name rule used by `run_sandboxed`. Paths, drive-qualified names, and traversal-like executable names are rejected before execution. A manifest therefore cannot bypass the sandbox executable allowlist.

## Audit without execution

```bash
lumen-capabilities list
```

This command parses and validates the manifest document, then prints profiles in deterministic name order. It does not execute a subprocess.

## Execute through a manifest

```bash
lumen-capabilities run --manifest python-basic -- python -c "print('hello')"
```

Manifest mode uses the profile's executable allowlist, timeout, and output limit. It cannot be combined with `--allow`, `--timeout`, or `--max-output-bytes`; mixing named policy with manual overrides would make the effective policy harder to audit.

The manual path remains available for one-off controlled runs:

```bash
lumen sandbox --allow python --timeout 2 -- python -c "print('hello')"
```

`lumen-capabilities run` also supports a manual `--allow` mode, but named manifests and manual settings are mutually exclusive.

## Security boundary

A capability manifest is an audit and convenience layer, not an operating-system security boundary. It does not add filesystem, network, syscall, or user isolation. An allowed executable still runs with the current user's OS permissions, inside the same temporary-workspace and minimal-environment containment provided by the existing sandbox runner.

Repository-owned manifest changes should therefore be reviewed as execution-policy changes. Adding a powerful executable can materially increase what an experiment may do even though the manifest schema itself remains valid.
