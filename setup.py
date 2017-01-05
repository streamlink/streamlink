#!/usr/bin/env python

from os import environ
from os.path import abspath, dirname, join
from setuptools import setup, find_packages
from sys import version_info, path as sys_path

deps = []

if version_info[0] == 2:
    # Require backport of concurrent.futures on Python 2
    deps.append("futures")

    # Require backport of argparse on Python 2.6
    if version_info[1] == 6:
        deps.append("argparse")

# Require singledispatch on Python <3.4
if version_info[0] == 2 or (version_info[0] == 3 and version_info[1] < 4):
    deps.append("singledispatch")

# requests 2.0 does not work correctly on Python <2.6.3
if (version_info[0] == 2 and version_info[1] == 6 and version_info[2] < 3):
    deps.append("requests>=1.0,<2.0")
else:
    deps.append("requests>=1.0,!=2.12.0,!=2.12.1,<3.0")

# this version of pycryptodome is known to work and has a Windows wheel for py2.7, py3.3-3.6
deps.append("pycryptodome>=3.4.3,<4")

# shutil.get_terminal_size and which were added in Python 3.3
if version_info[0] == 2:
    deps.append("backports.shutil_which")
    deps.append("backports.shutil_get_terminal_size")

# When we build an egg for the Win32 bootstrap we don't want dependency
# information built into it.
if environ.get("NO_DEPS"):
    deps = []

srcdir = join(dirname(abspath(__file__)), "src/")
sys_path.insert(0, srcdir)

setup(name="streamlink",
      version="0.2.0",
      description="Streamlink is command-line utility that extracts streams "
                  "from various services and pipes them into a video player of "
                  "choice.",
      url="https://github.com/streamlink/streamlink",
      author="Streamlink",
      author_email="charlie@charliedrage.com",  # temp until we have a mailing list / global email
      license="Simplified BSD",
      packages=find_packages("src"),
      package_dir={"": "src"},
      entry_points={
          "console_scripts": ["streamlink=streamlink_cli.main:main"]
      },
      install_requires=deps,
      test_suite="tests",
      classifiers=["Development Status :: 5 - Production/Stable",
                   "Environment :: Console",
                   "Operating System :: POSIX",
                   "Operating System :: Microsoft :: Windows",
                   "Programming Language :: Python :: 2.6",
                   "Programming Language :: Python :: 2.7",
                   "Programming Language :: Python :: 3.3",
                   "Programming Language :: Python :: 3.4",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Multimedia :: Sound/Audio",
                   "Topic :: Multimedia :: Video",
                   "Topic :: Utilities"])
