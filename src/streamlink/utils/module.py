from streamlink.compat import is_py3


def load_module(name, path=None):
    if is_py3:
        import importlib.machinery
        import importlib.util
        import sys

        loader_details = [(importlib.machinery.SourceFileLoader, importlib.machinery.SOURCE_SUFFIXES)]
        finder = importlib.machinery.FileFinder(path, *loader_details)
        spec = finder.find_spec(name)
        if not spec or not spec.loader:
            raise ImportError("no module named {0}".format(name))
        if sys.version_info[1] > 4:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        else:
            return spec.loader.load_module(name)

    else:
        import imp
        fd, filename, desc = imp.find_module(name, path and [path])
        try:
            return imp.load_module(name, fd, filename, desc)
        finally:
            if fd:
                fd.close()
