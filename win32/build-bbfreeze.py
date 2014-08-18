#!/usr/bin/env python
import os
import shutil
import sys

import bbfreeze.recipes

from itertools import ifilter
from bbfreeze import Freezer
from livestreamer import __version__

def recipe_pycparser(mf):
    m = mf.findNode("pycparser")
    if not m:
        return

    mf.import_hook("pycparser", m, ['*'])

    return True

bbfreeze.recipes.recipe_pycparser = recipe_pycparser

build_version = __version__
python_path = sys.prefix
script = os.path.join(python_path, "Scripts\\livestreamer-script.py")
script_exe = os.path.join(python_path, "Scripts\\livestreamer.py")

shutil.copy(script, script_exe)

includes = ("requests", "re", "xml", "xml.dom.minidom",
            "zlib", "ctypes", "argparse", "hmac", "tempfile",
            "os", "sys", "subprocess", "getpass", "msvcrt",
            "urllib", "urlparse", "pkgutil", "imp", "ast",
            "singledispatch", "cffi", "Crypto", "concurrent.futures")
manual_copy = ("librtmp", "librtmp_config", "librtmp_ffi")

freezer_path = os.path.dirname(os.path.abspath(__file__))
dst = "{0}\\..\\build-win32\\livestreamer-{1}-win32\\".format(freezer_path, build_version)
site_packages = next(ifilter(lambda p: p.endswith("site-packages"), sys.path))

f = Freezer(dst, includes=includes)
f.include_py = False
f.addScript(script_exe, gui_only=False)
f()

for pkg in manual_copy:
    src = os.path.join(site_packages, pkg)
    pkgdst = os.path.join(dst, pkg)
    shutil.copytree(src, pkgdst)

