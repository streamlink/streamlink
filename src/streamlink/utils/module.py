from __future__ import annotations

from importlib.machinery import FileFinder
from importlib.util import module_from_spec
from pathlib import Path
from pkgutil import get_importer
from types import ModuleType
from typing import TYPE_CHECKING, Union


if TYPE_CHECKING:  # pragma: no cover
    from _typeshed.importlib import PathEntryFinderProtocol


def get_finder(path: Union[Path, str]) -> PathEntryFinderProtocol:
    path = str(path)
    finder = get_importer(path)
    if not finder:
        raise ImportError(f"Not a package path: {path}", path=path)

    return finder


def load_module(name: str, path: Union[Path, str]) -> ModuleType:
    finder = get_finder(path)

    return exec_module(finder, name)


def exec_module(finder: PathEntryFinderProtocol, name: str) -> ModuleType:
    spec = finder.find_spec(name)
    if not spec or not spec.loader:
        raise ImportError(
            f"No module named '{name}'",
            name=name,
            path=finder.path if isinstance(finder, FileFinder) else None,
        )
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    return mod
