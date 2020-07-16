import re

from streamlink.stream import HTTPStream
from streamlink.plugin import Plugin


class Trovo(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?trovo\.live/")
    streams_re = re.compile(r'playUrl:"([^"]+)",desc:"([^"]+)"', re.DOTALL)

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        for m in self.streams_re.finditer(res.text):
            yield m.group(2), HTTPStream(self.session, m.group(1).replace('\\u002F', '/'))


__plugin__ = Trovo
