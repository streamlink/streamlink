#!/usr/bin/env python
import codecs
import os
import re
from os import environ, path
from sys import argv, path as sys_path

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

deps = [
    'importlib-metadata;python_version<"3.8"',
    'future;python_version<"3.0"',
    # Require backport of concurrent.futures on Python 2
    'futures;python_version<"3.0"',
    # Require singledispatch on Python <3.4
    'singledispatch;python_version<"3.4"',
    "requests>=2.26.0,<3.0",
    'urllib3[secure]>=1.23;python_version<"3.0"',
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
    # Require backport of functools.lru_cache on Python 2
    'backports.functools_lru_cache;python_version<"3.0"',
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

this_directory = path.abspath(path.dirname(__file__))
srcdir = path.join(this_directory, "src/")
sys_path.insert(0, srcdir)

with codecs.open(path.join(this_directory, "README.md"), "r", "utf8") as f:
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


entry_points = {"console_scripts": ["streamlink=streamlink_cli.main:main"]}

if is_wheel_for_windows():
    entry_points["gui_scripts"] = ["streamlinkw=streamlink_cli.main:main"]


def read(*parts):
    with codecs.open(os.path.join(here, *parts), "r") as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(
        r"""^__version__ = ['"]([^'"]*)['"]""",
        version_file,
        re.M,
    )
    if version_match:
        return version_match.group(1)

    raise RuntimeError("Unable to find version string.")


setup(
    name="streamlink",
    version=find_version("src", "streamlink", "__init__.py"),
    description="Streamlink is command-line utility that extracts streams "
    "from various services and pipes them into a video player of "
    "choice.",
    author="Streamlink",
    # temp until we have a mailing list / global email
    author_email="streamlink@protonmail.com",
    license="Simplified BSD",
    packages=find_packages("src"),
    package_dir={"": "src"},
    entry_points=entry_points,
    install_requires=deps,
    test_suite="tests",
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, <4",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: BSD License",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Video",
        "Topic :: Utilities",
    ],
)
