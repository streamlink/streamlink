import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate

YOUTUBE_URL = "https://www.youtube.com/watch?v={0}"
_url_re = re.compile(r'http(s)?://www\.skai.gr/.*')
_youtube_id = re.compile(r'<span\s+itemprop="contentUrl"\s+href="(.*)"></span>', re.MULTILINE)
_youtube_url_schema = validate.Schema(
    validate.all(
        validate.transform(_youtube_id.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.text
            )
        )
    )
)


class Skai(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        channel_id = http.get(self.url, schema=_youtube_url_schema)
        if channel_id:
            return self.session.streams(YOUTUBE_URL.format(channel_id))


__plugin__ = Skai
