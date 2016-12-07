import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import RTMPStream

_url_re = re.compile("^http(s)?://(\w+\.)?furstre\.am/stream/.+")
_stream_url_re = re.compile("<source src=\"([^\"]+)\"")
_schema = validate.Schema(
    validate.transform(_stream_url_re.search),
    validate.any(
        None,
        validate.all(
            validate.get(1),
            validate.url(
                scheme="rtmp"
            )
        )
    )
)


class Furstream(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        stream_url = http.get(self.url, schema=_schema)
        if not stream_url:
            return

        stream = RTMPStream(self.session, {
            "rtmp": stream_url,
            "pageUrl": self.url,
            "live": True
        })

        return dict(live=stream)

__plugin__ = Furstream
