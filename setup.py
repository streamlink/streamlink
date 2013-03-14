#!/usr/bin/env python

from setuptools import setup
from sys import version_info, path as sys_path
from os.path import abspath, dirname, join

deps = ["requests>=1.0,<2.0"]
packages = ["livestreamer",
            "livestreamer.stream",
            "livestreamer.plugins",
            "livestreamer.packages",
            "livestreamer.packages.flashmedia"]

# require argparse on Python <2.7 and <3.2
if (version_info[0] == 2 and version_info[1] < 7) or \
   (version_info[0] == 3 and version_info[1] < 2):
    deps.append("argparse")


srcdir = join(dirname(abspath(__file__)), "src/")
sys_path.insert(0, srcdir)

import livestreamer

setup(name="livestreamer",
      version=livestreamer.__version__,
      description="CLI program that launches streams from various streaming services in a custom video player.",
      url="http://livestreamer.tanuki.se/",
      author="Christopher Rosell",
      author_email="chrippa@tanuki.se",
      license="Simplified BSD",
      packages=packages,
      package_dir={ "": "src" },
      entry_points={
          "console_scripts": ["livestreamer=livestreamer.cli:main"]
      },
      install_requires=deps,
      test_suite="tests",
      classifiers=["Operating System :: POSIX",
                   "Operating System :: Microsoft :: Windows",
                   "Environment :: Console",
                   "Development Status :: 5 - Production/Stable",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Multimedia :: Sound/Audio",
                   "Topic :: Multimedia :: Video",
                   "Topic :: Utilities"]
)
