"""
$description Global live-streaming platform for the creative community.
$url piczel.tv
$type live
$metadata id
$metadata author
$metadata title
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(
    re.compile(r"https?://piczel\.tv/watch/(?P<channel>\w+)"),
)
class Piczel(Plugin):
    _URL_STREAMS = "https://piczel.tv/api/streams"
    _URL_HLS = "https://playback.piczel.tv/live/{id}/llhls.m3u8?_HLS_legacy=YES"

    def _get_streams(self):
        channel = self.match.group("channel")

        data = self.session.http.get(
            self._URL_STREAMS,
            params={
                "followedStreams": "false",
                "live_only": "false",
                "sfw": "false",
            },
            schema=validate.Schema(
                validate.parse_json(),
                [
                    {
                        "slug": str,
                        "live": bool,
                        "id": int,
                        "username": str,
                        "title": str,
                    },
                ],
                validate.filter(lambda item: item["slug"] == channel),
                validate.get(0),
                validate.any(
                    None,
                    validate.union_get(
                        "id",
                        "username",
                        "title",
                        "live",
                    ),
                ),
            ),
        )
        if not data:
            return

        self.id, self.author, self.title, is_live = data
        if not is_live:
            return

        return HLSStream.parse_variant_playlist(self.session, self._URL_HLS.format(id=self.id))


__plugin__ = Piczel
