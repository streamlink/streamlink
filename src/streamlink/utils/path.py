from pathlib import Path
from shutil import which
from typing import List, Optional, Union


def resolve_executable(
    custom: Optional[Union[str, Path]] = None,
    names: Optional[List[str]] = None,
    fallbacks: Optional[List[Union[str, Path]]] = None,
) -> Optional[Union[str, Path]]:
    if custom:
        return which(custom)

    for item in (names or []) + (fallbacks or []):
        executable = which(item)
        if executable:
            return executable

    return None
