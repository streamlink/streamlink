from importlib.abc import PathEntryFinder
from importlib.machinery import FileFinder
from importlib.util import module_from_spec
from pathlib import Path
from pkgutil import get_importer
from types import ModuleType
from typing import Union


def load_module(name: str, path: Union[Path, str]) -> ModuleType:
    path = str(path)
    finder = get_importer(path)
    if not finder:
        raise ImportError(f"Not a package path: {path}", path=path)

    return exec_module(finder, name)


def exec_module(finder: PathEntryFinder, name: str) -> ModuleType:
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
