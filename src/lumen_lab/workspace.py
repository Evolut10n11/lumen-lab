from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

DEFAULT_USER_ID = "default"
USER_ID_ENV = "LUMEN_USER_ID"
_USER_ID_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,62}[A-Za-z0-9])?$")


def validate_user_id(value: str) -> str:
    """Validate a stable local user identifier without allowing path traversal."""
    candidate = value.strip()
    if not candidate:
        raise ValueError("user id must be a non-empty string")
    if not _USER_ID_RE.fullmatch(candidate):
        raise ValueError(
            "user id must be 1-64 characters using only letters, numbers, '.', '_' or '-', "
            "and must start and end with a letter or number"
        )
    return candidate


def resolve_user_id(explicit: str | None = None) -> str:
    """Resolve CLI/app identity without consulting repository-owned profile state."""
    candidate = explicit if explicit is not None else os.environ.get(USER_ID_ENV, DEFAULT_USER_ID)
    return validate_user_id(candidate)


@dataclass(frozen=True, slots=True)
class UserWorkspace:
    """Machine-local, per-user state boundary for personalized Lumen behavior."""

    root: Path
    user_id: str

    @classmethod
    def from_root(
        cls,
        root: Path | str | None = None,
        user_id: str | None = None,
    ) -> UserWorkspace:
        resolved_root = Path.cwd() if root is None else Path(root)
        return cls(root=resolved_root, user_id=resolve_user_id(user_id))

    @property
    def directory(self) -> Path:
        return self.root / ".lumen" / "users" / self.user_id

    @property
    def profile_path(self) -> Path:
        return self.directory / "profile.json"

    @property
    def onboarding_context_path(self) -> Path:
        return self.directory / "onboarding_context.json"

    @property
    def github_context_path(self) -> Path:
        return self.directory / "github_context.json"

    @property
    def missions_path(self) -> Path:
        return self.directory / "missions.json"

    @property
    def work_sessions_path(self) -> Path:
        return self.directory / "work_sessions.json"

    @property
    def work_progress_path(self) -> Path:
        return self.directory / "work_progress.json"

    @property
    def feedback_path(self) -> Path:
        return self.directory / "feedback.json"

    @property
    def proposals_path(self) -> Path:
        return self.directory / "proposals.json"

    @property
    def backlog_path(self) -> Path:
        return self.directory / "backlog.json"

    @property
    def outcomes_path(self) -> Path:
        return self.directory / "outcomes.json"

    @property
    def journal_path(self) -> Path:
        return self.directory / "journal.md"

    def ensure(self) -> UserWorkspace:
        self.directory.mkdir(parents=True, exist_ok=True)
        return self

    def _quarantine_invalid_profile(self) -> None:
        if not self.profile_path.exists():
            return
        backup = self.profile_path.with_name(
            f"profile.corrupt-{uuid.uuid4().hex[:8]}.json"
        )
        try:
            os.replace(self.profile_path, backup)
        except OSError:
            # Recovery should never make bootstrap fail harder than the original state.
            pass

    def initialized(self) -> bool:
        if not self.profile_path.is_file():
            return False

        # v0.1.1 could truncate profile.json before a UnicodeEncodeError. Recover by
        # preserving the bad file and returning the user to onboarding.
        try:
            from .profile import load_profile

            profile = load_profile(self.profile_path)
        except (OSError, UnicodeError, ValueError):
            self._quarantine_invalid_profile()
            return False
        if profile.id != self.user_id:
            self._quarantine_invalid_profile()
            return False
        return True

    def require_initialized(self) -> None:
        if self.initialized():
            return
        raise ValueError(
            f"user workspace '{self.user_id}' is not initialized; run "
            f"`lumen-user --user {self.user_id} init ...` first"
        )
