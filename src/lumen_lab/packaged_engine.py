from __future__ import annotations

from .desktop_bridge import dispatch
from .stdio_protocol import serve


def main() -> int:
    # PyInstaller uses an isolated interpreter: Python environment variables are
    # not a reliable way to configure its streams. The protocol owns the bytes.
    return serve(dispatch)


if __name__ == "__main__":
    raise SystemExit(main())
