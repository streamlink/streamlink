#!/usr/bin/env python

build_version = "1.4.1"
python_path = "C:\\Python27\\"

import os
import glob
import shutil

from bbfreeze import Freezer

shutil.copy(python_path + "Scripts\livestreamer-script.py", python_path + "Scripts\livestreamer.py")

includes = ("pbs", "requests", "re", "xml", "xml.dom.minidom",
            "zlib", "ctypes", "argparse", "hmac", "tempfile",
            "os", "sys", "subprocess", "getpass", "msvcrt",
            "urllib", "urlparse", "pkgutil", "imp")

dst = "..\\build-win32\\livestreamer-bbfreeze-" + build_version + "\\"

f = Freezer(dst, includes=includes)
f.include_py = False
f.addScript(python_path + "Scripts\livestreamer.py", gui_only=False)

f()



