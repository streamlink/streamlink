#!/usr/bin/env python
import os
import shutil
import sys

from bbfreeze import Freezer
from livestreamer import __version__

build_version = __version__
python_path = sys.prefix
script = os.path.join(python_path, "Scripts\\livestreamer-script.py")
script_exe = os.path.join(python_path, "Scripts\\livestreamer.py")

shutil.copy(script, script_exe)

includes = ("requests", "re", "xml", "xml.dom.minidom",
            "zlib", "ctypes", "argparse", "hmac", "tempfile",
            "os", "sys", "subprocess", "getpass", "msvcrt",
            "urllib", "urlparse", "pkgutil", "imp", "ast")

freezer_path = os.path.dirname(os.path.abspath(__file__))
dst = "{0}\\..\\build-win32\\livestreamer-bbfreeze-{1}\\".format(freezer_path, build_version)

f = Freezer(dst, includes=includes)
f.include_py = False
f.addScript(script_exe, gui_only=False)
f()



