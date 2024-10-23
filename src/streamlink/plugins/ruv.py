"""
$description Live TV channels and video on-demand service from RUV, an Icelandic public, state-owned broadcaster.
$url ruv.is
$type live, vod
$region Iceland
"""

import logging
import re
from textwrap import dedent

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(r"https?://(?:www\.)?ruv\.is/(?:sjonvarp|utvarp)/beint/(?P<channel>\w+)$"),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(r"https?://(?:www\.)?ruv\.is/(?:sjonvarp|utvarp)/spila/[^/]+/(?P<id>\d+)/(?P<episode>[^/]+)/?"),
)
class Ruv(Plugin):
    _URL_API_CHANNEL = "https://geo.spilari.ruv.is/channel/{channel}"
    _URL_API_GQL = "https://spilari.nyr.ruv.is/gql/"

    def _get_live(self):
        url = self.session.http.get(
            self._URL_API_CHANNEL.format(channel=self.match["channel"]),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "url": validate.url(),
                },
                validate.get("url"),
            ),
        )
        if self.session.http.head(url, raise_for_status=False).status_code >= 400:
            log.error("The content is not available in your region")
            return

        return HLSStream.parse_variant_playlist(self.session, url)

    def _get_vod(self):
        query = f"""
            query getProgram($id: Int!) {{
              Program(id: $id) {{
                title
                episodes(limit: 1, id: {{value: "{self.match["episode"]}"}}) {{
                  title
                  file
                }}
              }}
            }}
        """

        self.author, self.title, url = self.session.http.post(
            self._URL_API_GQL,
            json={
                "operationName": "getProgram",
                "query": dedent(query).strip(),
                "variables": {
                    "id": int(self.match["id"]),
                },
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "Program": {
                            "episodes": validate.list(
                                {
                                    "file": validate.url(),
                                    "title": str,
                                },
                            ),
                            "title": str,
                        },
                    },
                },
                validate.get(("data", "Program")),
                validate.union_get(
                    "title",
                    ("episodes", 0, "title"),
                    ("episodes", 0, "file"),
                ),
            ),
        )

        if not url.endswith(".m3u8"):
            return {"vod": HTTPStream(self.session, url)}
        else:
            return HLSStream.parse_variant_playlist(self.session, url)

    def _get_streams(self):
        if self.matches["live"]:
            return self._get_live()
        else:
            return self._get_vod()


__plugin__ = Ruv
