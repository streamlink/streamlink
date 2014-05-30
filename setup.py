#!/usr/bin/env python

from setuptools import setup
from sys import version_info, path as sys_path
from os.path import abspath, dirname, join

deps = []
packages = ["livestreamer",
            "livestreamer.stream",
            "livestreamer.plugin",
            "livestreamer.plugin.api",
            "livestreamer.plugins",
            "livestreamer.packages",
            "livestreamer.packages.flashmedia",
            "livestreamer_cli"]

# require argparse on Python <2.7 and <3.2
if (version_info[0] == 2 and version_info[1] < 7) or \
   (version_info[0] == 3 and version_info[1] < 2):
    deps.append("argparse")

# requests 2.0 does not work correctly on Python <2.6.3
if (version_info[0] == 2 and version_info[1] == 6 and version_info[2] < 3):
    deps.append("requests>=1.0,<2.0")
else:
    deps.append("requests>=1.0,<3.0")


srcdir = join(dirname(abspath(__file__)), "src/")
sys_path.insert(0, srcdir)

setup(name="livestreamer",
      version="1.8.2",
      description="Livestreamer is CLI program that extracts streams from "
                  "various services and pipes them into a video player of "
                  "choice.",
      url="http://livestreamer.tanuki.se/",
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
      classifiers=["Operating System :: POSIX",
                   "Operating System :: Microsoft :: Windows",
                   "Environment :: Console",
                   "Development Status :: 5 - Production/Stable",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Multimedia :: Sound/Audio",
                   "Topic :: Multimedia :: Video",
                   "Topic :: Utilities"]
)
