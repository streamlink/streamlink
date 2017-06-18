import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HLSStream

HLS_URL_FORMAT = "https://hls.goodgame.ru/hls/{0}{1}.m3u8"
QUALITIES = {
    "1080p": "",
    "720p": "_720",
    "480p": "_480",
    "240p": "_240"
}

_url_re = re.compile(r"https?://(?:www\.)?goodgame.ru/channel/(?P<user>\w+)")
_stream_re = re.compile(r'var src = "([^"]+)";')
_ddos_re = re.compile(r'document.cookie="(__DDOS_[^;]+)')


class GoodGame(Plugin):
    @classmethod
    def can_handle_url(cls, url):
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
        if match:
            headers["Cookie"] = match.group(1)
            res = http.get(self.url, headers=headers)

        match = _stream_re.search(res.text)
        if not match:
            return

        stream_id = match.group(1)
        streams = {}
        for name, url_suffix in QUALITIES.items():
            url = HLS_URL_FORMAT.format(stream_id, url_suffix)
            if not self._check_stream(url):
                continue

            streams[name] = HLSStream(self.session, url)

        return streams


__plugin__ = GoodGame
