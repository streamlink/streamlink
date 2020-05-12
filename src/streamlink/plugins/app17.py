import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HTTPStream

API_URL = "https://api-dsa.17app.co/api/v1/lives/{0}/viewers/alive"

_url_re = re.compile(r"https://17.live/live/(?P<channel>[^/&?]+)")


class App17(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        self.session.http.headers.update({'User-Agent': useragents.CHROME, 'Referer': self.url})

        data = '{"liveStreamID":"%s"}' % (channel)

        try:
            res = self.session.http.post(API_URL.format(channel), data=data).json()
            http_url = res.get("rtmpUrls")[0].get("url")
        except Exception as e:
            self.logger.info("Stream currently unavailable.")
            return

        https_url = http_url.replace("http:", "https:")
        yield "live", HTTPStream(self.session, https_url)


__plugin__ = App17
