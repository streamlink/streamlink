import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class MRTmk(Plugin):
    url_re = re.compile(r"""https?://play\.mrt\.com\.mk/(live|play)/""")
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

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        stream_urls = self.stream_schema.validate(res.text)
        log.debug("Found streams: {0}".format(len(stream_urls)))
        if not stream_urls:
            return

        for stream_url in stream_urls:
            try:
                yield from HLSStream.parse_variant_playlist(self.session, stream_url).items()
            except OSError as err:
                if "403 Client Error" in str(err):
                    log.error("Failed to access stream, may be due to geo-restriction")
                else:
                    raise err


__plugin__ = MRTmk
