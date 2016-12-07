import re

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import RTMPStream, HTTPStream, HLSStream
from streamlink.utils import parse_json, rtmpparse, swfdecompress

_url_re = re.compile("http(s)?://api.dmcloud.net/player/embed/[^/]+/[^/]+")
_rtmp_re = re.compile(b"customURL[^h]+(https://.*?)\\\\")
_info_re = re.compile("var info = (.*);")
_schema = validate.Schema(
    {
        "mode": validate.text,
        validate.optional("mp4_url"): validate.url(scheme="http"),
        validate.optional("ios_url"): validate.url(scheme="http"),
        validate.optional("swf_url"): validate.url(scheme="http"),
    }
)


class DMCloud(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_rtmp_stream(self, swfurl):
        res = http.get(swfurl)
        swf = swfdecompress(res.content)
        match = _rtmp_re.search(swf)
        if not match:
            return

        res = http.get(match.group(1))
        rtmp, playpath = rtmpparse(res.text)
        params = {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "playpath": playpath,
            "swfUrl": swfurl,
            "live": True
        }

        return RTMPStream(self.session, params)

    def _get_streams(self):
        res = http.get(self.url)
        match = _info_re.search(res.text)
        if not match:
            return

        info = parse_json(match.group(1), schema=_schema)
        stream_name = info["mode"]
        mp4_url = info.get("mp4_url")
        ios_url = info.get("ios_url")
        swf_url = info.get("swf_url")

        if mp4_url:
            stream = HTTPStream(self.session, mp4_url)
            yield stream_name, stream

        if ios_url:
            if urlparse(ios_url).path.endswith(".m3u8"):
                streams = HLSStream.parse_variant_playlist(self.session, ios_url)
                # TODO: Replace with "yield from" when dropping Python 2.
                for stream in streams.items():
                    yield stream

        if swf_url:
            stream = self._get_rtmp_stream(swf_url)
            if stream:
                yield stream_name, stream


__plugin__ = DMCloud
