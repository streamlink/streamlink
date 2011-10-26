#!/usr/bin/env python3

from setuptools import setup, find_packages

version = "0.1"

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
      }
)
