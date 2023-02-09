"""
$description Live TV channels and video on-demand service from ARD, a German public, independent broadcaster.
$url daserste.de
$type live, vod
$region Germany
"""

import logging
import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://((www|live)\.)?daserste\.de/",
))
class ARDLive(Plugin):
    _URL_DATA_BASE = "https://www.daserste.de/"
    _QUALITY_MAP = {
        4: "1080p",
        3: "720p",
        2: "540p",
        1: "270p",
        0: "180p",
    }

    def _get_streams(self):
        try:
            data_url = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_find(".//*[@data-ctrl-player]"),
                validate.get("data-ctrl-player"),
                validate.transform(lambda s: s.replace("'", "\"")),
                validate.parse_json(),
                {"url": str},
                validate.get("url"),
            ))
        except PluginError:
            return

        data_url = urljoin(self._URL_DATA_BASE, data_url)
        log.debug(f"Player URL: '{data_url}'")

        self.title, media = self.session.http.get(data_url, schema=validate.Schema(
            validate.parse_json(name="MEDIAINFO"),
            {"mc": {
                validate.optional("_title"): str,
                "_mediaArray": [validate.all(
                    {
                        "_mediaStreamArray": [validate.all(
                            {
                                "_quality": validate.any(str, int),
                                "_stream": [validate.url()],
                            },
                            validate.union_get("_quality", ("_stream", 0)),
                        )],
                    },
                    validate.get("_mediaStreamArray"),
                    validate.transform(dict),
                )],
            }},
            validate.get("mc"),
            validate.union_get("_title", ("_mediaArray", 0)),
        ))

        if media.get("auto"):
            yield from HLSStream.parse_variant_playlist(self.session, media.get("auto")).items()
        else:
            for quality, stream in media.items():
                yield self._QUALITY_MAP.get(quality, quality), HTTPStream(self.session, stream)


__plugin__ = ARDLive
