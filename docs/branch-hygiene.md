# Branch hygiene

Lumen Lab keeps short-lived development branches disposable after their work is safely integrated.

The `Branch hygiene` workflow runs after a pull request is merged and once when the hygiene implementation itself lands on `main`.

It may delete only repository-local branches that are backed by explicit merge evidence:

- the head branch of a merged pull request;
- the head branch of a closed pull request explicitly referenced as `Supersedes #N` by a later merged pull request;
- the original branch for a merged `*-rebased` head when the merged pull request explicitly describes rebasing.

The cleanup always preserves:

- the default branch (`main`);
- protected branches;
- heads of currently open pull requests;
- unrelated work-in-progress branches with no merge/supersession evidence.

The Python entry point is dry-run by default. Deletion requires `--apply` and a `GITHUB_TOKEN` with repository contents write permission.

This policy intentionally prefers leaving an uncertain branch behind over deleting work without explicit evidence that it has been integrated or superseded.
