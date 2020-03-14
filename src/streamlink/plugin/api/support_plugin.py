import os
import inspect
from streamlink.utils import load_module

__all__ = ["load_support_plugin"]


def load_support_plugin(name):
    """Loads a plugin from the same directory as the calling plugin.

    The path used is extracted from the last call in module scope,
    therefore this must be called only from module level in the
    originating plugin or the correct plugin path will not be found.

    """

    # Get the path of the caller module
    stack = list(filter(lambda f: f[3] == "<module>", inspect.stack()))
    prev_frame = stack[0]
    path = os.path.dirname(prev_frame[1])

    # Major hack. If we are frozen by bbfreeze the stack trace will
    # contain relative paths. We therefore use the __file__ variable
    # in this module to correct it.
    if not os.path.isabs(path):
        prefix = os.path.normpath(__file__ + "../../../../../")
        path = os.path.join(prefix, path)

    return load_module(name, path)
