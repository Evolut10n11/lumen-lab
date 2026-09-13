# Experiment sandbox

`lumen sandbox` is a small process-containment layer for controlled experiments. It makes subprocess side effects more explicit without pretending to be a container, VM, or operating-system security boundary.

## Example

```bash
lumen sandbox --allow python --timeout 2 --max-output-bytes 4096 --json -- python -c "print('hello')"
```

Nothing is executable by default. Every command name must be explicitly repeated with `--allow NAME`, and the executable supplied after `--` must be a bare command name rather than a path.

## Guarantees

For each invocation Lumen:

- calls `subprocess.Popen` with `shell=False`;
- rejects path-like executable names before process creation;
- requires the executable name to be present in the explicit allowlist;
- resolves that bare name once and executes the resolved binary directly;
- creates a fresh temporary working directory;
- does not copy the parent process environment;
- provides only a small sandbox environment with temporary HOME/TMP locations;
- provides no stdin;
- enforces a timeout of at most 60 seconds;
- drains stdout and stderr concurrently so verbose processes cannot block on a full pipe;
- stores at most the configured number of bytes from each output stream in memory;
- removes the temporary working directory after the direct child exits;
- can emit a structured JSON result for later automation.

The default capture limit is 64 KiB per stream. The hard maximum is 1,000,000 bytes per stream.

## Threat model and limitations

This feature is intentionally conservative, but it is not a strong sandbox. An allowed executable still runs with the operating-system permissions of the current Lumen process. In particular, this layer does **not** prevent an allowed program from:

- opening absolute paths outside the temporary working directory;
- using the network;
- consuming CPU or memory before the timeout is reached;
- spawning descendant processes that may outlive the direct child;
- calling another executable through an absolute path if the allowed program itself chooses to do so;
- exploiting a vulnerability in the allowed executable or operating system.

For untrusted code, hostile inputs, or strong filesystem/network isolation, use an OS sandbox, container, disposable VM, or similarly enforced boundary. Lumen should only use this subprocess layer for controlled experiments whose executable and arguments are understood.

## Why this still helps

The goal is to replace accidental ambient authority with explicit execution intent. A normal subprocess inherits the current directory, environment variables, secrets, stdin, and effectively unlimited captured output unless the caller takes care to constrain them. `lumen sandbox` removes those defaults and produces an auditable result object.

That makes it suitable as a building block for future autonomous experiments while keeping stronger isolation as a separate, explicit capability rather than silently claiming it already exists.
