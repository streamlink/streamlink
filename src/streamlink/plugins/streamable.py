"""
$description Global video hosting platform.
$url streamable.com
$type vod
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream
from streamlink.utils.url import update_scheme


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?streamable\.com/(.+)"),
)
class Streamable(Plugin):
    def _get_streams(self):
        data = self.session.http.get(
            self.url,
            schema=validate.Schema(
                re.compile(r"var\s*videoObject\s*=\s*({.*?});"),
                validate.none_or_all(
                    validate.get(1),
                    validate.parse_json(),
                    {
                        "files": {
                            str: {
                                "url": validate.url(),
                                "width": int,
                                "height": int,
                                "bitrate": int,
                            },
                        },
                    },
                ),
            ),
        )

        for info in data["files"].values():
            stream_url = update_scheme("https://", info["url"])
            # pick the smaller of the two dimensions, for landscape v. portrait videos
            res = min(info["width"], info["height"])
            yield f"{res}p", HTTPStream(self.session, stream_url)


__plugin__ = Streamable
