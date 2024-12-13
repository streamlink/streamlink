from __future__ import annotations

import importlib
import inspect
import os
import sys
import warnings
from collections.abc import Callable, Mapping
from typing import Any


try:
    from builtins import BaseExceptionGroup, ExceptionGroup  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup  # type: ignore[import]


from streamlink.exceptions import StreamlinkDeprecationWarning


# compatibility import of charset_normalizer/chardet via requests<3.0
try:
    from requests.compat import chardet as charset_normalizer  # type: ignore
except ImportError:  # pragma: no cover
    import charset_normalizer


is_darwin = sys.platform == "darwin"
is_win32 = os.name == "nt"


detect_encoding = charset_normalizer.detect


def deprecated(items: Mapping[str, tuple[str | None, Any, Any]]) -> None:
    """
    Deprecate specific module attributes.

    This removes the deprecated attributes from the module's global context,
    adds/overrides the module's :func:`__getattr__` function, and emits a :class:`StreamlinkDeprecationWarning`
    if one of the deprecated attributes is accessed.

    :param items: A mapping of module attribute names to tuples which contain the following optional items:
                  1. an import path string (for looking up an external object while accessing the attribute)
                  2. a direct return object (if no import path was set)
                  3. a custom warning message
    """

    mod_globals = inspect.stack()[1].frame.f_globals
    orig_getattr: Callable[[str], Any] | None = mod_globals.get("__getattr__", None)

    def __getattr__(name: str) -> Any:
        if name in items:
            origin = f"{mod_globals['__spec__'].name}.{name}"
            path, obj, msg = items[name]
            warnings.warn(
                msg or f"'{origin}' has been deprecated",
                StreamlinkDeprecationWarning,
                stacklevel=2,
            )
            if path:
                *parts, name = path.split(".")
                imported = importlib.import_module(".".join(parts))
                obj = getattr(imported, name, None)

            return obj

        if orig_getattr is not None:
            return orig_getattr(name)

        raise AttributeError

    mod_globals["__getattr__"] = __getattr__

    # delete the deprecated module attributes and the imported `deprecated` function
    for item in items.keys() | [deprecated.__name__]:
        if item in mod_globals:
            del mod_globals[item]


__all__ = [
    "BaseExceptionGroup",
    "ExceptionGroup",
    "deprecated",
    "detect_encoding",
    "is_darwin",
    "is_win32",
]
