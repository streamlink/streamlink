import logging
import re
from typing import Tuple

import requests

from streamlink import __version__ as streamlink_version
from streamlink.cache import Cache


log = logging.getLogger("streamlink.cli")


def _parse_version(version: str) -> Tuple[int, int, int, int]:
    m = re.match(r"(\d+)\.(\d+)\.(\d+)(?:[+-](\d+))?", version)
    if not m:
        raise ValueError(f"Invalid version string: '{version}'")

    major, minor, patch, distance = m.groups()

    return int(major), int(minor), int(patch), (0 if distance is None else int(distance))


def get_latest() -> str:
    try:
        res = requests.get("https://pypi.python.org/pypi/streamlink/json")
        res.raise_for_status()
        data = res.json()
        return str(data.get("info").get("version"))
    except requests.exceptions.JSONDecodeError:
        log.error("Could not parse JSON data from PyPI API response")
    except Exception as err:
        log.error(f"Error while retrieving version data from PyPI API: {err}")
    return ""


def check_version(force: bool = False) -> bool:
    cache = Cache(filename="cli.json")
    latest_version = cache.get("latest_version")

    if force or not latest_version:
        latest_version = get_latest()
        if not latest_version:
            return False
        try:
            _parse_version(latest_version)
        except ValueError as err:
            log.error(f"Error while parsing version: {err}")
            return False

        cache.set("latest_version", latest_version, 60 * 60 * 24)

    version_info_printed = cache.get("version_info_printed")
    if not force and version_info_printed:
        return True

    if _parse_version(latest_version) > _parse_version(streamlink_version):
        log.info(f"A new version of Streamlink ({latest_version}) is available!")
        cache.set("version_info_printed", True, 60 * 60 * 6)
        return False
    elif force:
        log.info(f"Your Streamlink version ({streamlink_version}) is up to date!")

    return True
