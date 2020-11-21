import logging
import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)

HLS_URL_FORMAT = "https://hls.goodgame.ru/hls/{0}{1}.m3u8"
QUALITIES = {
    "1080p": "",
    "720p": "_720",
    "480p": "_480",
    "240p": "_240"
}

_url_re = re.compile(r"https?://(?:www\.)?goodgame.ru/channel/(?P<user>[^/]+)")
_apidata_re = re.compile(r'''(?P<quote>["']?)channel(?P=quote)\s*:\s*(?P<data>{.*?})\s*,''')
_ddos_re = re.compile(r'document.cookie="(__DDOS_[^;]+)')


class GoodGame(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _check_stream(self, url):
        res = self.session.http.get(url, acceptable_status=(200, 404))
        if res.status_code == 200:
            return True

    def _get_streams(self):
        headers = {
            "Referer": self.url
        }
        res = self.session.http.get(self.url, headers=headers)

        match = _ddos_re.search(res.text)
        if match:
            log.debug("Anti-DDOS bypass...")
            headers["Cookie"] = match.group(1)
            res = self.session.http.get(self.url, headers=headers)

        match = _apidata_re.search(res.text)
        channel_info = match and parse_json(match.group("data"))
        if not channel_info:
            log.error("Could not find channel info")
            return

        log.debug("Found channel info: id={id} channelkey={channelkey} pid={streamkey} online={status}".format(**channel_info))
        if not channel_info['status']:
            log.debug("Channel appears to be offline")

        streams = {}
        for name, url_suffix in QUALITIES.items():
            url = HLS_URL_FORMAT.format(channel_info['streamkey'], url_suffix)
            if not self._check_stream(url):
                continue

            streams[name] = HLSStream(self.session, url)

        return streams


__plugin__ = GoodGame
