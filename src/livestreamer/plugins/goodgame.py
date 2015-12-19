import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HLSStream

HLS_URL_FORMAT = "http://hls.goodgame.ru/hls/{0}{1}.m3u8"
QUALITIES = {
    "1080p": "",
    "720p": "_720",
    "480p": "_480",
    "240p": "_240"
}

_url_re = re.compile("http://(?:www\.)?goodgame.ru/channel/(?P<user>\w+)")
_stream_re = re.compile(
    "iframe frameborder=\"0\" width=\"100%\" height=\"100%\" src=\"http://goodgame.ru/player(\d)?\?(\w+)\""
)
_ddos_re = re.compile(
    "document.cookie=\"(__DDOS_[^;]+)"
)

class GoodGame(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _check_stream(self, url):
        res = http.get(url, acceptable_status=(200, 404))
        if res.status_code == 200:
            return True

    def _get_streams(self):
        headers = {
            "Referer": self.url
        }
        res = http.get(self.url, headers=headers)

        match = _ddos_re.search(res.text)
        if (match):
            headers["Cookie"] = match.group(1)
            res = http.get(self.url, headers=headers)

        match = _stream_re.search(res.text)
        if not match:
            return

        stream_id = match.group(2)
        streams = {}
        for name, url_suffix in QUALITIES.items():
            url = HLS_URL_FORMAT.format(stream_id, url_suffix)
            if not self._check_stream(url):
                continue

            streams[name] = HLSStream(self.session, url)

        return streams

__plugin__ = GoodGame
