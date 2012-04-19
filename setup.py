#!/usr/bin/env python3

from setuptools import setup, find_packages
from sys import version_info

version = "0.1"
deps = []

# require argparse on Python <2.7 and <3.2
if (version_info[0] == 2 and version_info[1] < 7) or \
   (version_info[0] == 3 and version_info[1] < 2):
    deps.append("argparse")

setup(name="livestreamer",
      version=version,
      description="Util to play various livestreaming services in custom player",
      author="Christopher Rosell",
      author_email="chrippa@tanuki.se",
      license="BSD",
      packages=["livestreamer", "livestreamer/plugins"],
      package_dir={'': 'src'},
      entry_points={
          "console_scripts": ['livestreamer=livestreamer.cli:main']
      },
      install_requires=deps
)
