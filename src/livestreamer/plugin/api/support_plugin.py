import os
import inspect
import sys

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

    # importlib is the preferred way of importing a module, but it's
    # only available on Python 3.1+.
    if sys.version_info[0] == 3 and sys.version_info[1] >= 3:
        import importlib

        loader = importlib.find_loader(name, [path])

        if loader:
            module = loader.load_module()
        else:
            raise ImportError("No module named '{0}'".format(name))
    else:
        import imp

        fd, filename, desc = imp.find_module(name, [path])

        try:
            module = imp.load_module(name, fd, filename, desc)
        finally:
            if fd: fd.close()

    return module

