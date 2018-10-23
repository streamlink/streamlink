import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream


class MeTube(Plugin):

    _url_re = re.compile(r"""https?://(?:www\.)?metube\.id/
                         (?P<type>live|videos)/\w+(?:/.*)?""", re.VERBOSE)

    # extracted from webpage source
    _VOD_STREAM_NAMES = {
        "3000k": "1080p",
        "1800k": "720p",
        "800k": "480p",
        "300k": "240p"
    }

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        stream_type = self._url_re.match(self.url).group("type")
        hls_re = re.compile(r"""["'](?P<url>[^"']+\.m3u8[^"']*?)["']""")

        headers = {
            "Origin": "https://www.metube.id",
            "User-Agent": useragents.FIREFOX
        }

        res = self.session.http.get(self.url)
        match = hls_re.search(res.text)

        if not match:
            return

        stream_url = match.group("url")

        if stream_type == "live":
            return HLSStream.parse_variant_playlist(self.session, stream_url,
                                                    headers=headers)
        else:
            streams = {}

            for quality, stream in HLSStream.parse_variant_playlist(
                                   self.session,
                                   stream_url,
                                   headers=headers).items():
                    name = self._VOD_STREAM_NAMES.get(quality, quality)
                    streams[name] = stream

            return streams


__plugin__ = MeTube
