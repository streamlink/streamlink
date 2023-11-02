"""
$description Japanese Internet visual radio "Super! A&G+" operated by Nippon Cultural Broadcasting (JOQR).
$url www.uniqueradio.jp/agplayer5
$url joqr.co.jp
$type live
$metadata author
$metadata title
"""

import re
from urllib.parse import unquote_plus, urljoin

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(r"https?://www\.uniqueradio\.jp/agplayer5/(?:player\.php|inc-player-hls\.php)"))
@pluginmatcher(re.compile(r"https?://(?:www\.)?joqr\.co\.jp/(?:ag|qr/(?:agdailyprogram|agregularprogram))"))
class JoqrAg(Plugin):
    _URL_HOST = "https://www.uniqueradio.jp"
    _URL_METADATA = f"{_URL_HOST}/aandg"
    _URL_PLAYER = f"{_URL_HOST}/agplayer5/inc-player-hls.php"

    def _get_streams(self):
        self.id = "live"
        self.author = "超!A&G+"

        self.title = self.session.http.get(
            self._URL_METADATA,
            schema=validate.Schema(
                validate.regex(re.compile(r"""var\s+Program_name\s*=\s*["\']([^"\']+)["\']""")),
                validate.none_or_all(
                    validate.get(1),
                    validate.transform(unquote_plus),
                ),
            ),
        )
        if self.title == "放送休止":
            raise NoStreamsError

        m3u8_url = self.session.http.get(
            self._URL_PLAYER,
            schema=validate.Schema(
                validate.regex(re.compile(r"""<source\s[^>]*\bsrc="([^"]+)"\s*""")),
                validate.none_or_all(
                    validate.get(1),
                    validate.transform(lambda m3u8_path: urljoin(self._URL_HOST, m3u8_path)),
                ),
            ),
        )

        return HLSStream.parse_variant_playlist(self.session, m3u8_url)


__plugin__ = JoqrAg
