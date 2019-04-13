"""
Plugin for dlive.tv
"""
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


QUALITY_WEIGHTS = {
   "src": 1080,
}


class DLive(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?dlive\.tv/")


    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "dlive"

        return Plugin.stream_weight(key)

    def _get_streams(self):
        res = self.session.http.get(self.url)

        _t_re = re.compile(r"(?<=user:)(\w|-)+")

        username = _t_re.search(res.text).group(0)

        hls_url = "https://live.prd.dlive.tv/hls/live/{}.m3u8".format(username)

        try:
            return HLSStream.parse_variant_playlist(self.session, hls_url)
        except Exception:
            return None

__plugin__ = DLive
