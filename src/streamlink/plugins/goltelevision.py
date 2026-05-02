"""
$description Spanish live TV sports channel owned by Gol Network.
$url goltelevision.com
$type live
$region Spain
"""

import re
from urllib.parse import urlparse

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate


log = getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?goltelevision\.com/en-directo"),
)
class GOLTelevision(Plugin):
    _provider_dailymotion = "https://www.dailymotion.com/embed/video/{video}"

    def _get_stream_data(self):
        return self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[@id='__NEXT_DATA__'][@type='application/json'][1]/text()"),
                validate.none_or_all(
                    validate.parse_json(),
                    {
                        "props": {
                            "pageProps": {
                                "channel": {
                                    "stream": {
                                        "dataVideo": str,
                                        "key": str,
                                        "metaContent": validate.url(),
                                    },
                                },
                            },
                        },
                    },
                    validate.get(("props", "pageProps", "channel", "stream")),
                    validate.union_get("dataVideo", "key", "metaContent"),
                ),
            ),
        )

    def _get_streams(self):
        if not (data := self._get_stream_data()):
            log.error("No stream data found")
            return

        data_video, key, meta_content = data

        match urlparse(meta_content).netloc.split("."), data_video, key:
            case host, *_ if host[-2:] == ["dailymotion", "com"] or host == ["dai", "ly"]:
                log.info("Found embedded dailymotion stream")
                return self.session.streams(self._provider_dailymotion.format(video=data_video))
            case _:
                log.error("No matching stream provider found for the embedded stream")
                return


__plugin__ = GOLTelevision
