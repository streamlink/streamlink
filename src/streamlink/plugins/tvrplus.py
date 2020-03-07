import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class TVRPlus(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?tvrplus\.ro/live/")
    hls_file_re = re.compile(r"""["'](?P<url>[^"']+\.m3u8(?:[^"']+)?)["']""")

    stream_schema = validate.Schema(
        validate.all(
            validate.transform(hls_file_re.findall),
            validate.any(None, [validate.text])
        ),
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        headers = {
            "User-Agent": useragents.FIREFOX,
            "Referer": self.url
        }
        stream_url = self.stream_schema.validate(self.session.http.get(self.url).text)
        if stream_url:
            stream_url = list(set(stream_url))
            for url in stream_url:
                self.logger.debug("URL={0}".format(url))
                for s in HLSStream.parse_variant_playlist(self.session, url, headers=headers).items():
                    yield s


__plugin__ = TVRPlus
