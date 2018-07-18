import re

from streamlink.compat import quote
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


def _filter_url(url):
    try:
        Welt._schema_url.validate(url)
        return True
    except:
        return False


class Welt(Plugin):
    _url_vod = "https://www.welt.de/onward/video/token/{0}"
    _re_url = re.compile(
        r"""https?://(\w+\.)?welt\.de/?""",
        re.IGNORECASE
    )
    _re_url_vod = re.compile(
        r"""mediathek""",
        re.IGNORECASE
    )
    _re_json = re.compile(
        r"""
            <script>\s*
            var\s+funkotron\s*=\s*
            \{\s*
                config\s*:\s*(?P<json>\{.+?\})\s*
            \}\s*;?\s*
            </script>
        """,
        re.VERBOSE | re.DOTALL | re.IGNORECASE
    )
    _schema = validate.Schema(
        validate.transform(_re_json.search),
        validate.get("json"),
        validate.transform(parse_json),
        validate.get("page"),
        validate.get("content"),
        validate.get("media"),
        validate.get(0),
        validate.get("sources"),
        validate.map(lambda obj: obj["file"]),
        validate.filter(_filter_url),
        validate.get(0)
    )
    _schema_url = validate.Schema(
        validate.url(
            scheme="https",
            path=validate.endswith(".m3u8")
        )
    )
    _schema_vod = validate.Schema(
        validate.transform(parse_json),
        validate.get("urlWithToken"),
        _schema_url
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._re_url.match(url) is not None

    def __init__(self, url):
        Plugin.__init__(self, url)
        self.url = url
        self.isVod = self._re_url_vod.search(url) is not None

    def _get_streams(self):
        headers = {"User-Agent": useragents.CHROME}
        hls_url = self.session.http.get(self.url, headers=headers, schema=self._schema)
        headers["Referer"] = self.url

        if self.isVod:
            url = self._url_vod.format(quote(hls_url, safe=""))
            hls_url = self.session.http.get(url, headers=headers, schema=self._schema_vod)

        return HLSStream.parse_variant_playlist(self.session, hls_url, headers=headers)


__plugin__ = Welt
