import re
from base64 import b64decode
from urllib.parse import unquote

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


@pluginmatcher(re.compile(
    r"https?://www\.rtp\.pt/play/"
))
class RTPPlay(Plugin):
    _m3u8_re = re.compile(r"""
        hls\s*:\s*(?:
            (["'])(?P<string>[^"']*)\1
            |
            decodeURIComponent\s*\((?P<obfuscated>\[.*?])\.join\(
            |
            atob\s*\(\s*decodeURIComponent\s*\((?P<obfuscated_b64>\[.*?])\.join\(
        )
    """, re.VERBOSE)

    _schema_hls = validate.Schema(
        validate.transform(lambda text: next(reversed(list(RTPPlay._m3u8_re.finditer(text))), None)),
        validate.any(
            None,
            validate.all(
                validate.get("string"),
                str,
                validate.any(
                    validate.length(0),
                    validate.url()
                )
            ),
            validate.all(
                validate.get("obfuscated"),
                str,
                validate.transform(lambda arr: unquote("".join(parse_json(arr)))),
                validate.url()
            ),
            validate.all(
                validate.get("obfuscated_b64"),
                str,
                validate.transform(lambda arr: unquote("".join(parse_json(arr)))),
                validate.transform(lambda b64: b64decode(b64).decode("utf-8")),
                validate.url()
            )
        )
    )

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.CHROME,
                                          "Referer": self.url})
        hls_url = self.session.http.get(self.url, schema=self._schema_hls)
        if hls_url:
            return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = RTPPlay
