"""
$description Turkish live TV channel owned by Kanal Beyaz.
$url beyaztv.com.tr
$type live
"""

import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate


@pluginmatcher(re.compile(
    r"https?://(?:www\.|m\.)?beyaztv\.com\.tr/canli-yayin",
))
class BeyazTV(Plugin):
    def _get_streams(self):
        video_id = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"""data-video=(?P<q>["'])(?P<video_id>\S+)(?P=q)"""),
            validate.any(None, validate.get("video_id")),
        ))

        if video_id:
            return self.session.streams(
                f"https://www.dailymotion.com/video/{video_id}",
            )


__plugin__ = BeyazTV
