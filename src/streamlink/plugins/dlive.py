"""
Plugin for dlive.tv
"""
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json
from streamlink.compat import unquote_plus


QUALITY_WEIGHTS = {
   "src": 1080,
}


class DLive(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?dlive\.tv/")
    _playback_re = re.compile(r"""(?<=playbackUrl":")(.+?)(?=")""")
    _username_re = re.compile(r"(?<=user:)(\w|-)+")


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

        playback_url = self._playback_re.search(res.text)

        if playback_url is not None:
            hls_url = playback_url.group(0)
            hls_url = bytes(unquote_plus(hls_url), "utf-8").decode("unicode_escape")
            print(hls_url)
        else:
            username = self._username_re.search(res.text)
            if username is not None:
                hls_url = "https://live.prd.dlive.tv/hls/live/{}.m3u8".format(
                    username.group(0))

        try:
            return HLSStream.parse_variant_playlist(self.session, hls_url)
        except Exception:
            return None

__plugin__ = DLive
