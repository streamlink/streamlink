import os
import sys

import subprocess

from ..compat import is_win32, shlex_quote, is_py2, is_py3
from ..constants import DEFAULT_FORMAT_ARGUMENTS

def check_paths(exes, paths):
    for path in paths:
        for exe in exes:
            path = os.path.expanduser(os.path.join(path, exe))
            if os.path.isfile(path):
                return path


def find_default_player():
    if "darwin" in sys.platform:
        paths = os.environ.get("PATH", "").split(":")
        paths += ["/Applications/VLC.app/Contents/MacOS/"]
        paths += ["~/Applications/VLC.app/Contents/MacOS/"]
        path = check_paths(("VLC", "vlc"), paths)
    elif "win32" in sys.platform:
        exename = "vlc.exe"
        paths = os.environ.get("PATH", "").split(";")
        path = check_paths((exename,), paths)

        if not path:
            subpath = "VideoLAN\\VLC\\"
            envvars = ("PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432")
            paths = filter(None, (os.environ.get(var) for var in envvars))
            paths = (os.path.join(p, subpath) for p in paths)
            path = check_paths((exename,), paths)
    else:
        paths = os.environ.get("PATH", "").split(":")
        path = check_paths(("vlc",), paths)

    if path:
        # Quote command because it can contain space
        return subprocess.list2cmdline([path])

def sanitizeTitle(wholeTitle):
    if wholeTitle is None:
        wholeTitle = DEFAULT_FORMAT_ARGUMENTS["title"]
    
    if not is_win32:
        if is_py2:
            title = shlex_quote(wholeTitle.encode('utf8'))
        elif is_py3:
            title = shlex_quote(wholeTitle)
    else:
        if is_py2:
            title = subprocess.list2cmdline([wholeTitle.encode('utf8')])
        elif is_py3:
            title = subprocess.list2cmdline([wholeTitle])
    title = title.replace("$","$$")
    return title
