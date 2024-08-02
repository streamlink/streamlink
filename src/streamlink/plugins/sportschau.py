"""
$description German sports magazine live streams and VOD content, owned by ARD.
$url sportschau.de
$type live
$metadata id
$metadata title
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"https?://(?:\w+\.)*sportschau\.de/"))
class Sportschau(Plugin):
    _schema_media = validate.Schema(
        validate.parse_html(),
        validate.xml_xpath_string(".//*[@data-v-type='MediaPlayer'][@data-v][1]/@data-v"),
        validate.none_or_all(
            validate.parse_json(),
            {
                "mc": {
                    validate.optional("id"): str,
                    "meta": {
                        "title": str,
                    },
                    "streams": [
                        validate.all(
                            {
                                "media": [
                                    validate.all(
                                        {
                                            "mimeType": str,
                                            "url": validate.url(),
                                        },
                                        validate.union_get(
                                            "mimeType",
                                            "url",
                                        ),
                                    ),
                                ],
                            },
                            validate.get("media"),
                        ),
                    ],
                },
            },
            validate.get("mc"),
            validate.union_get(
                "id",
                ("meta", "title"),
                "streams",
            ),
        ),
    )

    def _get_streams(self):
        data = self.session.http.get(self.url, schema=self._schema_media)
        if not data:
            return

        self.id, self.title, streams = data

        for media in streams:
            for mime_type, url in media:
                if mime_type == "application/vnd.apple.mpegurl":
                    yield from HLSStream.parse_variant_playlist(self.session, url).items()
                elif mime_type.startswith("audio/"):
                    yield "audio", HTTPStream(self.session, url)


__plugin__ = Sportschau
