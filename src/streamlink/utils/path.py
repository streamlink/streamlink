from __future__ import annotations

from pathlib import Path
from shutil import which


def resolve_executable(
    custom: str | Path | None = None,
    names: list[str] | None = None,
    fallbacks: list[str | Path] | None = None,
) -> str | Path | None:
    if custom:
        return which(custom)

    for item in (names or []) + (fallbacks or []):
        executable = which(item)
        if executable:
            return executable

    return None
