import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class MRTmk(Plugin):
    url_re = re.compile(r"""https?://play.mrt.com.mk/(live|play)/""")
    file_re = re.compile(r"""(?P<url>https?://vod-[\d\w]+\.interspace\.com[^"',]+\.m3u8[^"',]*)""")

    stream_schema = validate.Schema(
        validate.all(
            validate.transform(file_re.finditer),
            validate.transform(list),
            [validate.get("url")],
            # remove duplicates
            validate.transform(set),
            validate.transform(list),
        ),
    )

    def __init__(self, url):
        super(MRTmk, self).__init__(url)

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        stream_urls = self.stream_schema.validate(res.text)
        self.logger.debug("Found {0} stream URL{1}", len(stream_urls),
                          "" if len(stream_urls) == 1 else "s")

        for stream_url in stream_urls:
            for s in HLSStream.parse_variant_playlist(self.session, stream_url).items():
                yield s


__plugin__ = MRTmk
