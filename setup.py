#!/usr/bin/env python

from os import environ
from os.path import abspath, dirname, join
from setuptools import setup
from sys import version_info, path as sys_path

deps = []
packages = [
    "livestreamer",
    "livestreamer.stream",
    "livestreamer.plugin",
    "livestreamer.plugin.api",
    "livestreamer.plugins",
    "livestreamer.packages",
    "livestreamer.packages.flashmedia",
    "livestreamer_cli",
    "livestreamer_cli.packages",
    "livestreamer_cli.utils"
]

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
    deps.append("requests>=1.0,<3.0")

# When we build an egg for the Win32 bootstrap we don't want dependency
# information built into it.
if environ.get("NO_DEPS"):
    deps = []

srcdir = join(dirname(abspath(__file__)), "src/")
sys_path.insert(0, srcdir)

setup(name="livestreamer",
      version="1.12.2",
      description="Livestreamer is command-line utility that extracts streams "
                  "from various services and pipes them into a video player of "
                  "choice.",
      url="http://livestreamer.io/",
      author="Christopher Rosell",
      author_email="chrippa@tanuki.se",
      license="Simplified BSD",
      packages=packages,
      package_dir={ "": "src" },
      entry_points={
          "console_scripts": ["livestreamer=livestreamer_cli.main:main"]
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
                   "Topic :: Utilities"]
)
