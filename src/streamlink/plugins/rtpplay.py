"""
$description Live TV channels and video on-demand service from RTP, a Portuguese public, state-owned broadcaster.
$url rtp.pt/play
$type live, vod
$region Portugal
"""

import re
from base64 import b64decode

from streamlink.compat import unquote
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://www\.rtp\.pt/play/"
))
class RTPPlay(Plugin):
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
                validate.text,
                validate.any(
                    validate.length(0),
                    validate.url()
                )
            ),
            validate.all(
                validate.get("obfuscated"),
                validate.text,
                validate.parse_json(),
                validate.transform(lambda arr: unquote("".join(arr))),
                validate.url()
            ),
            validate.all(
                validate.get("obfuscated_b64"),
                validate.text,
                validate.parse_json(),
                validate.transform(lambda arr: unquote("".join(arr))),
                validate.transform(lambda b64: b64decode(b64).decode("utf-8")),
                validate.url()
            )
        )
    )

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.CHROME,
                                          "Referer": self.url})
        hls_url = self.session.http.get(self.url, schema=self._schema_hls)
        if not hls_url:
            return
        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = RTPPlay
