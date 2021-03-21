import re
from urllib.parse import unquote

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


class RTPPlay(Plugin):
    _url_re = re.compile(r"https?://www\.rtp\.pt/play/")
    _m3u8_re = re.compile(r"""
        hls:\s*(?:(["'])(?P<string>[^"']+)\1
        |
        decodeURIComponent\((?P<obfuscated>\[.*?])\.join\()
    """, re.VERBOSE)

    _schema_hls = validate.Schema(
        validate.transform(_m3u8_re.search),
        validate.any(
            None,
            validate.all(
                validate.get("string"),
                validate.url()
            ),
            validate.all(
                validate.get("obfuscated"),
                validate.transform(lambda arr: unquote("".join(parse_json(arr)))),
                validate.url()
            )
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.CHROME,
                                          "Referer": self.url})
        hls_url = self.session.http.get(self.url, schema=self._schema_hls)
        if not hls_url:
            return
        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = RTPPlay
