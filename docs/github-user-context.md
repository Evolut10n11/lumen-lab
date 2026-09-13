# GitHub user context

GitHub is Lumen's first optional external context source.

The product goal is not to turn GitHub activity into another score. It is to give Lumen better evidence about what the user is actually building, maintaining, learning, and returning to over time.

## Current user experience

The shipped first version uses opt-in public GitHub context:

```text
Profile / Connections
→ enter a GitHub username
→ preview public account/repository evidence
→ connect
→ Lumen stores a user-scoped snapshot
→ context hypotheses and recommendations update
```

The normal user does not have to create or paste a personal access token or use the CLI.

Authenticated GitHub access can be added later behind the same context adapter when private or collaboration evidence becomes necessary.

## Evidence used today

The public-context adapter normalizes:

- account identity and public profile metadata;
- public repositories owned by the account;
- recently pushed repositories;
- repository language mix;
- recent public event counts;
- repository topics and descriptions as weak project-intent evidence.

Lumen derives product context from these signals conservatively. A repository existing does not prove that it is currently important, so GitHub hypotheses remain lower-confidence than explicit first-run answers.

## Recommendation effect

Connected GitHub context now affects recommendations instead of being display-only.

Lumen combines two different kinds of evidence:

1. the user's explicit top priority from the local profile;
2. the most active public repository from the normalized GitHub snapshot.

When both are available, Lumen creates one temporary, low-risk GitHub-derived mission such as:

```text
Use agent-kit to move Ship a stronger portfolio forward
```

The mission is tagged with the explicit priority, repository, repository short name, primary language when available, and `github`. Because the mission still goes through the normal deterministic mission scorer, the explicit priority remains the reason it can rank highly; GitHub activity alone does not bypass the profile.

Refreshing GitHub replaces the previous GitHub-derived mission instead of accumulating stale project recommendations. Disconnecting GitHub removes the derived mission, its work-session template, and any progress tied to that derived mission while leaving ordinary user-created/profile-derived work untouched.

## Trust rules

1. GitHub is optional. Lumen works without it.
2. Public context is fetched only after an explicit preview/connect action.
3. GitHub evidence is stored separately from first-run answers and behavior signals.
4. External activity updates context and can create a bounded derived mission; it does not silently overwrite explicit user statements.
5. The user can disconnect GitHub and delete cached GitHub-derived context and work.
6. Tokens are not required by the public-context implementation and must never be stored in repository files or normal plaintext runtime JSON if authenticated access is added later.
7. Derived work must keep normal risk, profile-alignment, feedback, and deterministic-ranking rules.

## Authentication direction

If Lumen later needs authenticated GitHub data, a native desktop client should use a browser-based GitHub authorization flow rather than asking the user for a token.

The authentication provider should stay behind an adapter so the app can move between GitHub OAuth/GitHub App authorization approaches without changing the personalization engine.

The desktop UI should expose connection state, last sync time, the categories of evidence being used, disconnect, and refresh controls.

## Context boundary

GitHub data enters the personalization system as evidence, not authority:

```text
GitHub API
→ normalized GitHub evidence
→ user-scoped integration snapshot
→ context hypotheses
→ bounded GitHub-derived mission
→ normal ranking / feedback / clarification rules
```

The ranking engine never consumes raw GitHub API responses directly.
