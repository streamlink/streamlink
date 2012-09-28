#!/usr/bin/env python

from setuptools import setup, find_packages
from sys import version_info

version = "1.3.1"
deps = ["pbs", "requests>=0.12.1"]

# require argparse on Python <2.7 and <3.2
if (version_info[0] == 2 and version_info[1] < 7) or \
   (version_info[0] == 3 and version_info[1] < 2):
    deps.append("argparse")

setup(name="livestreamer",
      version=version,
      description="CLI program that launches streams from various streaming services in a custom video player",
      url="https://github.com/chrippa/livestreamer",
      author="Christopher Rosell",
      author_email="chrippa@tanuki.se",
      license="BSD",
      packages=["livestreamer", "livestreamer.stream", "livestreamer.plugins"],
      package_dir={'': 'src'},
      entry_points={
          "console_scripts": ['livestreamer=livestreamer.cli:main']
      },
      install_requires=deps,
      classifiers=["Operating System :: POSIX",
                   "Operating System :: Microsoft :: Windows",
                   "Environment :: Console",
                   "Development Status :: 5 - Production/Stable",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Multimedia :: Sound/Audio",
                   "Topic :: Utilities"]
)
