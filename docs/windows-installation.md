# Windows installation

Lumen is packaged as a normal Windows desktop application. End users do not need Python, Node.js, Rust, Git, PowerShell, or a virtual environment.

## Install

1. Download the latest `Lumen_*_x64-setup.exe` build from a GitHub Release. During development, the same setup executable is also produced as the `lumen-windows-installer-*` artifact by the **Windows Installer** GitHub Actions workflow.
2. Run the setup executable.
3. Finish the installer and open **Lumen** from the Windows Start menu/application shortcut.
4. On first launch, complete the short conversational introduction. Lumen creates a local workspace and begins with a tentative understanding of your current context and goals.

The installer uses a per-user installation, so administrator privileges are not required for the normal install path.

## What is included

The setup package contains both layers needed to run Lumen:

- the React + Tauri desktop application;
- a standalone packaged Lumen engine built from the Python application code.

The desktop host starts the bundled engine automatically. A normal installed copy does not call a system Python interpreter.

Personal product state is written to the operating-system application data directory chosen by Tauri. It is not stored inside the installed program files and is not shared with other Lumen users.

## First-run experience

A fresh installation should follow this path:

```text
Install Lumen
→ Open Lumen
→ short introduction
→ starting context and hypotheses
→ personalized missions
→ normal usage teaches Lumen what fits
```

GitHub context remains optional. If a user chooses to connect a public GitHub profile, Lumen previews the information first and only saves it after explicit confirmation.

## Development builds

The Windows packaging workflow performs these checks before publishing an installer artifact:

```text
build standalone lumen-engine.exe
→ run a bootstrap smoke test without Python
→ stage the engine inside the Tauri bundle
→ build the NSIS setup executable
→ upload the resulting installer artifact
```

Tagged versions (`v*`) are configured to publish the generated setup executable to GitHub Releases automatically.

## Current limitation: code signing

Development installers are currently unsigned. Windows may therefore show a SmartScreen/reputation warning on machines that have never seen the binary before. Production distribution should add Authenticode code signing before presenting Lumen as a frictionless public download.

This warning is about publisher reputation/signing; it is separate from whether the application contains its own engine or requires Python.