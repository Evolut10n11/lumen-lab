# GitHub Issues bridge

The bridge mirrors pending Lumen experiments into GitHub Issues so autonomous work is visible without making GitHub a hidden source of truth.

## Commands

Preview the desired issues without making any network request:

```bash
lumen github-sync
```

Compare with GitHub and apply only Lumen-managed creates or updates:

```bash
lumen github-sync --apply --repository Evolut10n11/lumen-lab
```

For an applied sync, provide a token through `GITHUB_TOKEN` or `--token`. Dry-run mode never reads a token and never contacts GitHub.

## Ownership marker

Every managed issue contains a marker such as:

```html
<!-- lumen-lab:exp-001 -->
```

An issue without this exact marker is treated as human-owned, even if its title looks like a Lumen issue. The bridge therefore cannot take over a similarly named human issue by accident.

## Safety rules

1. Only experiments in `backlog` or `active` are represented as desired issues.
2. The default mode is dry-run and has zero network side effects.
3. Applied sync requires an explicit repository and token.
4. The bridge may create a missing managed issue or update an existing managed issue.
5. The bridge never closes issues. A completed or dropped experiment simply disappears from the desired set.
6. The bridge never edits an issue that lacks a Lumen ownership marker.
7. Pull requests returned by GitHub's Issues API are ignored.
8. The bridge does not use third-party dependencies and does not persist tokens.

These constraints intentionally make synchronization conservative. Closing completed issues can be added later only if the lab has enough evidence that ownership and lifecycle matching are reliable.
