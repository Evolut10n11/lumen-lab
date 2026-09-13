from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .sandbox import (
    SandboxError,
    SandboxResult,
    _validate_bare_executable,
    run_sandboxed,
)

_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_OUTPUT_BYTES = 64 * 1024


class CapabilityError(ValueError):
    """Raised when a capability manifest or selection is invalid."""


@dataclass(frozen=True, slots=True)
class CapabilityManifest:
    name: str
    executables: tuple[str, ...]
    timeout_seconds: float
    max_output_bytes: int
    description: str = ""

    def validate(self) -> None:
        if not _NAME_PATTERN.fullmatch(self.name):
            raise CapabilityError(
                "manifest name must match [a-z0-9][a-z0-9-]{0,63}"
            )
        if not self.executables:
            raise CapabilityError(
                f"manifest {self.name!r} must allow at least one executable"
            )

        normalized: set[str] = set()
        for executable in self.executables:
            try:
                _validate_bare_executable(executable)
            except SandboxError as exc:
                raise CapabilityError(
                    f"manifest {self.name!r} has invalid executable "
                    f"{executable!r}: {exc}"
                ) from exc
            key = os.path.normcase(executable)
            if key in normalized:
                raise CapabilityError(
                    f"manifest {self.name!r} contains duplicate executable "
                    f"{executable!r}"
                )
            normalized.add(key)

        if not 0 < self.timeout_seconds <= 60:
            raise CapabilityError(
                "timeout_seconds must be greater than 0 and at most 60"
            )
        if not 0 < self.max_output_bytes <= 1_000_000:
            raise CapabilityError(
                "max_output_bytes must be between 1 and 1000000"
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CapabilityManifest:
        name = data.get("name")
        executables = data.get("executables")
        timeout = data.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
        output_limit = data.get("max_output_bytes", DEFAULT_MAX_OUTPUT_BYTES)
        description = data.get("description", "")

        if not isinstance(name, str):
            raise CapabilityError("manifest name must be a string")
        if not isinstance(executables, list) or not all(
            isinstance(item, str) for item in executables
        ):
            raise CapabilityError(
                f"manifest {name!r} executables must be a list of strings"
            )
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise CapabilityError(
                f"manifest {name!r} timeout_seconds must be numeric"
            )
        if isinstance(output_limit, bool) or not isinstance(output_limit, int):
            raise CapabilityError(
                f"manifest {name!r} max_output_bytes must be an integer"
            )
        if not isinstance(description, str):
            raise CapabilityError(
                f"manifest {name!r} description must be a string"
            )

        manifest = cls(
            name=name,
            executables=tuple(executables),
            timeout_seconds=float(timeout),
            max_output_bytes=output_limit,
            description=description.strip(),
        )
        manifest.validate()
        return manifest


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    source: str
    allowed_executables: tuple[str, ...]
    timeout_seconds: float
    max_output_bytes: int


def load_capability_manifests(path: Path) -> list[CapabilityManifest]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CapabilityError(
            f"capability manifest file not found: {path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise CapabilityError(f"invalid capability manifest JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise CapabilityError("capability manifest document must be a JSON object")
    items = raw.get("manifests")
    if not isinstance(items, list):
        raise CapabilityError(
            "capability manifest document must contain a manifests list"
        )

    manifests: list[CapabilityManifest] = []
    names: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise CapabilityError(
                "each capability manifest must be a JSON object"
            )
        manifest = CapabilityManifest.from_dict(item)
        if manifest.name in names:
            raise CapabilityError(
                f"duplicate capability manifest name: {manifest.name}"
            )
        names.add(manifest.name)
        manifests.append(manifest)
    return sorted(manifests, key=lambda item: item.name)


def get_manifest(
    manifests: list[CapabilityManifest],
    name: str,
) -> CapabilityManifest:
    for manifest in manifests:
        if manifest.name == name:
            return manifest
    raise CapabilityError(f"unknown capability manifest: {name}")


def resolve_execution_policy(
    manifests: list[CapabilityManifest],
    *,
    manifest_name: str = "",
    manual_allowed: tuple[str, ...] = (),
    timeout_override: float | None = None,
    max_output_override: int | None = None,
) -> ExecutionPolicy:
    if manifest_name:
        if manual_allowed or timeout_override is not None or max_output_override is not None:
            raise CapabilityError(
                "manifest mode cannot be combined with --allow, --timeout, "
                "or --max-output-bytes"
            )
        manifest = get_manifest(manifests, manifest_name)
        return ExecutionPolicy(
            source=f"manifest:{manifest.name}",
            allowed_executables=manifest.executables,
            timeout_seconds=manifest.timeout_seconds,
            max_output_bytes=manifest.max_output_bytes,
        )

    if not manual_allowed:
        raise CapabilityError(
            "choose --manifest NAME or provide at least one --allow NAME"
        )
    return ExecutionPolicy(
        source="manual",
        allowed_executables=manual_allowed,
        timeout_seconds=(
            DEFAULT_TIMEOUT_SECONDS if timeout_override is None else timeout_override
        ),
        max_output_bytes=(
            DEFAULT_MAX_OUTPUT_BYTES
            if max_output_override is None
            else max_output_override
        ),
    )


def run_with_policy(argv: list[str], policy: ExecutionPolicy) -> SandboxResult:
    return run_sandboxed(
        argv,
        allowed_executables=policy.allowed_executables,
        timeout_seconds=policy.timeout_seconds,
        max_output_bytes=policy.max_output_bytes,
    )


def render_manifest_list(manifests: list[CapabilityManifest]) -> str:
    if not manifests:
        return "No capability manifests are configured.\n"
    lines = ["NAME                 TIMEOUT  MAX_OUTPUT  EXECUTABLES  DESCRIPTION"]
    for manifest in sorted(manifests, key=lambda item: item.name):
        executables = ",".join(manifest.executables)
        lines.append(
            f"{manifest.name:<20} {manifest.timeout_seconds:>7.1f}s  "
            f"{manifest.max_output_bytes:>10}  {executables:<12}  "
            f"{manifest.description}"
        )
    return "\n".join(lines) + "\n"
