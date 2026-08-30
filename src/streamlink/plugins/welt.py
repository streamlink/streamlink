"""
$description German news and documentaries TV channel, owned by Axel Springer SE.
$url welt.de
$type live, vod
$metadata title
$region Germany
$notes Some VODs are mp4 which may not stream, use -o to download
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


@pluginmatcher(
    re.compile(r"https?://(\w+\.)?welt\.de/?"),
)
class Welt(Plugin):
    _re_vod_quality = re.compile(r"_(\d+)\.mp4$")

    def _get_streams(self):
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string("""
                    .//script
                    [starts-with(@data-internal-ref,'WeltVideoPlayer-') or @data-content='VideoPlayer.Config']
                    /text()
                """),
                validate.none_or_all(
                    str,
                    validate.parse_json(),
                    {
                        "title": str,
                        "sources": [
                            validate.all(
                                {
                                    "src": validate.url(),
                                    "extension": str,
                                },
                                validate.union_get("extension", "src"),
                            ),
                        ],
                    },
                    validate.union_get("sources", "title"),
                ),
            ),
        )
        if not data:
            return

        sources, self.title = data

        self.session.http.headers.update({"Referer": self.url})

        http_streams = {}
        for extension, src in sources:
            if extension == "m3u8":
                return HLSStream.parse_variant_playlist(self.session, src)
            if extension == "mp4":
                quality = self._re_vod_quality.search(src)
                if quality:
                    http_streams[f"{quality[1]}k"] = HTTPStream(self.session, src)

        return http_streams


__plugin__ = Welt
