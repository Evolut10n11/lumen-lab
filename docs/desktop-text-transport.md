# Desktop text transport

The desktop wire protocol is JSON over explicit UTF-8 bytes. It must not depend on Windows ANSI/OEM code pages, PowerShell settings, or Python environment variables. PyInstaller embeds an isolated interpreter and may ignore PYTHONUTF8/PYTHONIOENCODING.

The previous implementation used sys.stdin.read()/sys.stdout.write() and a lossy UTF-8 decoder in Rust. With legacy Windows streams, original Russian labels became replacement characters while a user-supplied goal could appear correct after two opposite encoding mistakes. A successful bootstrap-only smoke test did not catch this.

## Contract

- The engine decodes stdin.buffer as strict UTF-8 (an optional UTF-8 BOM is accepted).
- Malformed UTF-8 is rejected before dispatch; no code-page guessing or silent byte replacement.
- Responses are Unicode-escaped JSON encoded explicitly as UTF-8 bytes. JSON escaping preserves Cyrillic, emoji and other scripts exactly.
- Lone surrogate handling remains at the JSON boundary; valid non-BMP characters are preserved.
- Development and frozen desktop launches use the same packaged_engine entry point.
- Rust treats invalid UTF-8 on stdout as a protocol error; only stderr diagnostics may use lossy decoding.

## Validation

`tests/test_stdio_protocol.py` exercises cp1251, cp1252, cp866, ASCII and UTF-8 TextIOWrappers and reproduces the previous corruption path.

`packaging/check_engine_text.py` sends real UTF-8 bytes to the built executable, checks exact names, goals, Cyrillic UI strings and emoji, completes a step, starts new processes, switches ru/en/ru, and checks persisted UTF-8 JSON and stable progress. The Windows workflow runs this against both the standalone executable and the executable from an installed NSIS bundle before uploading the installer.

These are engine/transport checks, not a claim that the Windows WebView was interactively tested.

## Existing user data

On startup, Lumen repairs the lossless UTF-8/Windows-1251, UTF-8/Windows-1252, or UTF-8/Latin-1 mojibake patterns produced by older desktop builds. It scans only valid per-user JSON, requires a high-confidence marker reduction, preserves colliding key spellings, writes repaired state atomically, and keeps each original file beside it with a `.before-encoding-repair` suffix. Normal Russian and Western text is left unchanged, and users do not need to repeat onboarding or delete AppData.

Characters that an older decoder replaced or discarded cannot be reconstructed. Those uncommon lossy cases remain visible rather than being guessed silently.
