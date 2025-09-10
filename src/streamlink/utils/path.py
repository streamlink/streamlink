from __future__ import annotations

from shutil import which
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


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
