from __future__ import annotations

import re
from typing import TYPE_CHECKING

from streamlink import __version__ as streamlink_version, validate
from streamlink.cache import Cache
from streamlink.logger import getLogger


if TYPE_CHECKING:
    from streamlink.session import Streamlink


log = getLogger("streamlink.cli")


def _parse_version(version: str) -> tuple[int, int, int, int]:
    m = re.match(r"(\d+)\.(\d+)\.(\d+)(?:[+-](\d+))?", version)
    if not m:
        raise ValueError(f"Invalid version string: '{version}'")

    major, minor, patch, distance = m.groups()

    return int(major), int(minor), int(patch), (0 if distance is None else int(distance))


def get_latest(session: Streamlink) -> str:
    try:
        return session.http.get(
            "https://pypi.python.org/pypi/streamlink/json",
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "info": {
                        "version": str,
                    },
                },
                validate.get(("info", "version")),
            ),
        )
    except Exception as err:
        log.error(f"Error while retrieving version data from PyPI API: {getattr(err, 'err', err)}")
    return ""


def check_version(session: Streamlink, force: bool = False) -> bool:
    cache = Cache(filename="cli.json")
    latest_version = cache.get("latest_version")

    if force or not latest_version:
        latest_version = get_latest(session)
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
