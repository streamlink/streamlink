#!/usr/bin/env python
import os
import shutil
import sys

from bbfreeze import Freezer

build_version = "1.4.4"
python_path = sys.prefix
script = os.path.join(python_path, "Scripts\\livestreamer-script.py")
script_exe = os.path.join(python_path, "Scripts\\livestreamer.py")

shutil.copy(script, script_exe)

includes = ("requests", "re", "xml", "xml.dom.minidom",
            "zlib", "ctypes", "argparse", "hmac", "tempfile",
            "os", "sys", "subprocess", "getpass", "msvcrt",
            "urllib", "urlparse", "pkgutil", "imp")

dst = "..\\build-win32\\livestreamer-bbfreeze-" + build_version + "\\"

f = Freezer(dst, includes=includes)
f.include_py = False
f.addScript(script_exe, gui_only=False)
f()



