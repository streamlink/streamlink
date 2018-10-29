import os
import sys

import subprocess


def check_paths(exes, paths):
    for path in paths:
        for exe in exes:
            path = os.path.expanduser(os.path.join(path, exe))
            if os.path.isfile(path):
                return path


def find_default_player():
    if "darwin" in sys.platform:
        paths = os.environ.get("PATH", "").split(":")
        paths += ["/Applications/MPV.app/Contents/MacOS/"]
        paths += ["~/Applications/MPV.app/Contents/MacOS/"]
        path = check_paths(("MPV", "mpv"), paths)
    elif "win32" in sys.platform:
        exename = "mpv.exe"
        paths = os.environ.get("PATH", "").split(";")
        path = check_paths((exename,), paths)

        if not path:
            subpath = "mpv-x86_64\\"
            envvars = ("PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432")
            paths = filter(None, (os.environ.get(var) for var in envvars))
            paths = (os.path.join(p, subpath) for p in paths)
            path = check_paths((exename,), paths)
    else:
        paths = os.environ.get("PATH", "").split(":")
        path = check_paths(("mpv",), paths)

    if path:
        # Quote command because it can contain space
        return subprocess.list2cmdline([path])
