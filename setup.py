#!/usr/bin/env python

from setuptools import setup, find_packages
from sys import version_info
from os import name as os_name
import os

version = "1.4"
deps = ["requests>=0.12.1"]
packages = ["livestreamer",
            "livestreamer.stream",
            "livestreamer.plugins",
            "livestreamer.packages",
            "livestreamer.packages.flashmedia"]

# require argparse on Python <2.7 and <3.2
if (version_info[0] == 2 and version_info[1] < 7) or \
   (version_info[0] == 3 and version_info[1] < 2):
    deps.append("argparse")

if os_name == "nt":
    deps.append("pbs")
else:
    deps.append("sh")

setup(name="livestreamer",
      version=version,
      description="CLI program that launches streams from various streaming services in a custom video player",
      url="https://github.com/chrippa/livestreamer",
      author="Christopher Rosell",
      author_email="chrippa@tanuki.se",
      license="BSD",
      packages=packages,
      package_dir={'': 'src'},
      entry_points={
          "console_scripts": ['livestreamer=livestreamer.cli:main']
      },
      install_requires=deps,
      test_suite="tests",
      classifiers=["Operating System :: POSIX",
                   "Operating System :: Microsoft :: Windows",
                   "Environment :: Console",
                   "Development Status :: 5 - Production/Stable",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Multimedia :: Sound/Audio",
                   "Topic :: Utilities"]
)
