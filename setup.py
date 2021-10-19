#!/usr/bin/env python
import codecs
import sys
from os import environ, path
from sys import argv, path as sys_path
from textwrap import dedent

from setuptools import find_packages, setup

import versioneer


def format_msg(text, *args, **kwargs):
    return dedent(text).strip(" \n").format(*args, **kwargs)


CURRENT_PYTHON = sys.version_info[:2]
REQUIRED_PYTHON = (3, 6)

# This check and everything above must remain compatible with older Python versions
if CURRENT_PYTHON < REQUIRED_PYTHON:
    sys.exit(format_msg("""
        ========================================================
                       Unsupported Python version
        ========================================================
        This version of Streamlink requires at least Python {}.{},
        but you're trying to install it on Python {}.{}.

        This may be because you are using a version of pip that
        doesn't understand the python_requires classifier.
        Make sure you have pip >= 9.0 and setuptools >= 24.2
    """, *(REQUIRED_PYTHON + CURRENT_PYTHON)))

# Explicitly disable running tests via setuptools
if "test" in sys.argv:
    sys.exit(format_msg("""
        Running `python setup.py test` has been deprecated since setuptools 41.5.0.
        Streamlink requires pytest for collecting and running tests, via one of these commands:
        `pytest` or `python -m pytest` (see the pytest docs for more infos about this)
    """))


data_files = []
deps = [
    "requests>=2.26.0,<3.0",
    "isodate",
    "lxml>=4.6.3",
    "websocket-client>=0.58.0",
    # Support for SOCKS proxies
    "PySocks!=1.5.7,>=1.5.6",
    # win-inet-pton is missing a dependency in PySocks, this has been fixed but not released yet
    # Required due to missing socket.inet_ntop & socket.inet_pton method in Windows Python 2.x
    'win-inet-pton;python_version<"3.0" and platform_system=="Windows"',
    # shutil.get_terminal_size and which were added in Python 3.3
    'backports.shutil_which;python_version<"3.3"',
    'backports.shutil_get_terminal_size;python_version<"3.3"',
    "js2py"
]

# for encrypted streams
if environ.get("STREAMLINK_USE_PYCRYPTO"):
    deps.append("pycrypto")
else:
    # this version of pycryptodome is known to work and has a Windows wheel for py2.7, py3.3-3.6
    deps.append("pycryptodome>=3.4.3,<4")

# for localization
if environ.get("STREAMLINK_USE_PYCOUNTRY"):
    deps.append("pycountry")
else:
    deps.append("iso-639")
    deps.append("iso3166")

# When we build an egg for the Win32 bootstrap we don"t want dependency
# information built into it.
if environ.get("NO_DEPS"):
    deps = []

this_directory = path.abspath(path.dirname(__file__))
srcdir = path.join(this_directory, "src/")
sys_path.insert(0, srcdir)

with codecs.open(path.join(this_directory, "README.md"), 'r', "utf8") as f:
    long_description = f.read()


def is_wheel_for_windows():
    if "bdist_wheel" in argv:
        names = ["win32", "win-amd64", "cygwin"]
        length = len(argv)
        for pos in range(argv.index("bdist_wheel") + 1, length):
            if argv[pos] == "--plat-name" and pos + 1 < length:
                return argv[pos + 1] in names
            elif argv[pos][:12] == "--plat-name=":
                return argv[pos][12:] in names
    return False


entry_points = {
    "console_scripts": ["streamlink=streamlink_cli.main:main"]
}

if is_wheel_for_windows():
    entry_points["gui_scripts"] = ["streamlinkw=streamlink_cli.main:main"]


# optional data files
additional_files = [
    # shell completions
    #  requires pre-built completion files via shtab (dev-requirements.txt)
    #  `./script/build-shell-completions.sh`
    ("share/bash-completion/completions", ["build/shtab/bash/streamlink"]),
    ("share/zsh/site-functions", ["build/shtab/zsh/_streamlink"]),
    # man page
    #  requires pre-built man page file via sphinx (docs-requirements.txt)
    #  `make --directory=docs clean man`
    ("share/man/man1", ["docs/_build/man/streamlink.1"])
]

for destdir, srcfiles in additional_files:
    files = []
    for srcfile in srcfiles:
        if path.exists(srcfile):
            files.append(srcfile)
    if files:
        data_files.append((destdir, files))


setup(name="streamlink",
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      description="Streamlink is a command-line utility that extracts streams "
                  "from various services and pipes them into a video player of "
                  "choice.",
      long_description=long_description,
      long_description_content_type="text/markdown",
      url="https://github.com/streamlink/streamlink",
      project_urls={
          "Documentation": "https://streamlink.github.io/",
          "Tracker": "https://github.com/streamlink/streamlink/issues",
          "Source": "https://github.com/streamlink/streamlink",
          "Funding": "https://opencollective.com/streamlink"
      },
      author="Streamlink",
      # temp until we have a mailing list / global email
      author_email="streamlink@protonmail.com",
      license="Simplified BSD",
      packages=find_packages("src"),
      package_dir={"": "src"},
      package_data={"streamlink.plugins": [".removed"]},
      entry_points=entry_points,
      data_files=data_files,
      install_requires=deps,
      test_suite="tests",
      python_requires=">=3.6, <4",
      classifiers=["Development Status :: 5 - Production/Stable",
                   "License :: OSI Approved :: BSD License",
                   "Environment :: Console",
                   "Intended Audience :: End Users/Desktop",
                   "Operating System :: POSIX",
                   "Operating System :: Microsoft :: Windows",
                   "Operating System :: MacOS",
                   "Programming Language :: Python :: 3",
                   "Programming Language :: Python :: 3 :: Only",
                   "Programming Language :: Python :: 3.6",
                   "Programming Language :: Python :: 3.7",
                   "Programming Language :: Python :: 3.8",
                   "Programming Language :: Python :: 3.9",
                   "Topic :: Internet :: WWW/HTTP",
                   "Topic :: Multimedia :: Sound/Audio",
                   "Topic :: Multimedia :: Video",
                   "Topic :: Utilities"])
