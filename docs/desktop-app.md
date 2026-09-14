# Lumen desktop app

The CLI remains a development and debugging surface. The user product is a desktop application.

## Product flow

A normal user should never need PowerShell, Python commands, JSON state files, or ranking controls.

The desktop flow is:

```text
Launch Lumen
    ↓
First run? ── yes ──> quick onboarding
    │                   name + 1–5 goals
    │                         ↓
    no                    personalized home
    ↓                         ↓
personalized home ─────> focus session
                              ↓
                       progress + passive learning
```

The main product surfaces are:

- **Today** — one recommended next move, an optional explanation of the evidence behind it, and lightweight steering actions;
- **Focus** — the current bounded work session, progress, and the same recommendation explanation;
- **Activity** — mission radar and momentum summary;
- **Profile** — personalization state without exposing tuning controls.

## Architecture

```text
React UI
  │
  │ Tauri invoke
  ▼
Tauri host (Rust)
  │
  │ JSON over stdin/stdout
  ▼
Python desktop bridge
  │
  ▼
LumenApplication
  │
  ▼
per-user local workspace
```

The UI does not reimplement ranking or personalization. It renders the application-service contract and sends explicit product actions back to the Python engine.

Recommendation explanations follow the same boundary: Python computes `today.selection.reasons`; React only renders those reasons in a collapsed detail and suppresses the already-visible `why_now` duplicate. The frontend does not reconstruct score weights or infer new evidence.

## Local data and trust boundary

The Tauri host resolves the operating system's application-data directory and launches the Python bridge with that directory as its working directory. The existing `UserWorkspace` abstraction therefore stores runtime state under the Lumen app-data area rather than inside the Git checkout.

The data root is host-controlled by design. The webview request contains only an action, user ID, and action payload; the Python bridge always uses its process working directory and ignores any caller-supplied `root` field. This prevents a compromised or malformed UI request from redirecting Lumen state writes to another path that the current user can access.

No user should need to know that `.lumen/users/<user-id>/` exists.

## Development on Windows

From the repository root, install the Python project once:

```powershell
python -m pip install -e ".[dev]"
```

Then install the desktop dependencies:

```powershell
cd apps\desktop
npm install
```

Run the desktop application from a terminal where the project virtual environment is active:

```powershell
npm run tauri dev
```

If the desktop host cannot resolve the intended Python interpreter, point it at the active environment explicitly:

```powershell
$env:LUMEN_PYTHON = (Resolve-Path "..\..\.venv\Scripts\python.exe")
npm run tauri dev
```

The end-user build will not require this setup. Packaging the Python engine as a sidecar and producing an installer are separate release tasks.

## Release direction

The intended Windows deliverable is a normal installer and Start-menu shortcut. The release pipeline should eventually:

1. build the Python engine into a self-contained sidecar;
2. bundle that sidecar with Tauri;
3. build and sign the Windows installer;
4. launch Lumen without Python, Node, Rust, or terminal requirements on the user's machine.

CLI commands remain useful for maintainers but are not the primary product path.
