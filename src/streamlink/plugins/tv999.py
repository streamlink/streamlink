import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils.url import update_scheme

log = logging.getLogger(__name__)


class TV999(Plugin):
    url_re = re.compile(r'https?://(?:www\.)?tv999\.bg/live\.html')
    iframe_re = re.compile(r'<iframe.*src="([^"]+)"')
    hls_re = re.compile(r'src="([^"]+)"\s+type="application/x-mpegURL"')

    iframe_schema = validate.Schema(
        validate.transform(iframe_re.search),
        validate.any(None, validate.all(
            validate.get(1),
            validate.url(),
        )),
    )

    hls_schema = validate.Schema(
        validate.transform(hls_re.search),
        validate.any(None, validate.all(
            validate.get(1),
            validate.transform(lambda x: update_scheme('http:', x)),
            validate.url(),
        )),
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        iframe_url = self.session.http.get(self.url, schema=self.iframe_schema)

        if not iframe_url:
            log.error('Failed to find IFRAME URL')
            return

        hls_url = self.session.http.get(iframe_url, schema=self.hls_schema)

        if hls_url:
            return {'live': HLSStream(self.session, hls_url)}


__plugin__ = TV999
