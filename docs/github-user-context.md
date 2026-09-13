# GitHub user context

GitHub is Lumen's first planned optional external context source.

The product goal is not to turn GitHub activity into another score. It is to give Lumen better evidence about what the user is actually building, maintaining, learning, and returning to over time.

## User experience

The intended desktop flow is:

```text
Profile / Connections
→ Connect GitHub
→ Lumen opens GitHub authorization
→ user grants access
→ Lumen explains what it found
→ user chooses whether to use that context
```

The normal user should never have to create or paste a personal access token or use the CLI.

## Evidence we want

Useful first-version signals include:

- account identity and public profile metadata;
- repositories the authorized user can see;
- recently updated repositories;
- repository language mix;
- ownership versus collaboration;
- recent contribution/activity timestamps where the API can provide them reliably;
- topics and descriptions as weak project-intent evidence.

Lumen should derive product context from these signals conservatively. A repository existing does not prove that it is currently important.

## Trust rules

1. GitHub is optional. Lumen works without it.
2. The app explains what it will read before requesting access.
3. GitHub evidence is stored separately from first-run answers and behavior signals.
4. External activity updates confidence; it does not silently overwrite explicit user statements.
5. The user can disconnect GitHub and delete cached GitHub-derived context.
6. Tokens must not be stored in repository files or normal plaintext runtime JSON.
7. Lumen should request the narrowest useful permissions.

## Authentication direction

For a native desktop client, authentication should use a browser-based GitHub authorization flow rather than asking the user for a token.

The first implementation should keep the authentication provider behind an adapter so the app can move between GitHub OAuth/GitHub App authorization approaches without changing the personalization engine.

The desktop UI should expose connection state, last sync time, the categories of evidence being used, disconnect, and refresh controls.

## Context boundary

GitHub data should enter the personalization system as evidence, not authority:

```text
GitHub API
→ normalized GitHub evidence
→ user-scoped integration snapshot
→ context hypotheses / mission evidence
→ normal ranking and clarification rules
```

The ranking engine should never depend directly on raw API responses.
