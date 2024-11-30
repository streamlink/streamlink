from __future__ import annotations

import sys
from importlib.machinery import FileFinder
from importlib.util import module_from_spec
from pathlib import Path
from pkgutil import get_importer
from types import ModuleType
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from _typeshed.importlib import PathEntryFinderProtocol


def get_finder(path: str | Path) -> PathEntryFinderProtocol:
    path = str(path)
    finder = get_importer(path)
    if not finder:
        raise ImportError(f"Not a package path: {path}", path=path)

    return finder


def load_module(name: str, path: str | Path, override: bool = False) -> ModuleType:
    finder = get_finder(path)

    return exec_module(finder, name, override)


def exec_module(finder: PathEntryFinderProtocol, name: str, override: bool = False) -> ModuleType:
    spec = finder.find_spec(name)
    if not spec or not spec.loader:
        raise ImportError(
            f"No module named '{name}'",
            name=name,
            path=finder.path if isinstance(finder, FileFinder) else None,
        )

    if not override and (mod := sys.modules.get(spec.name)):
        return mod

    mod = module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    return mod
