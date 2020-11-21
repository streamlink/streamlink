import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


class CBSNews(Plugin):
    url_re = re.compile(r"https://www\.cbsnews\.com/live/")
    _re_default_payload = re.compile(r"CBSNEWS.defaultPayload = (\{.*)")

    _schema_items = validate.Schema(
        validate.transform(_re_default_payload.search),
        validate.any(None, validate.all(
            validate.get(1),
            validate.transform(parse_json),
            {"items": [validate.all({
                "video": validate.url(),
                "format": "application/x-mpegURL"
            }, validate.get("video"))]},
            validate.get("items")
        ))
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        items = self.session.http.get(self.url, schema=self._schema_items)
        if items:
            for hls_url in items:
                yield from HLSStream.parse_variant_playlist(self.session, hls_url).items()


__plugin__ = CBSNews
