import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?tv360\.com\.tr/canli-yayin"
))
class TV360(Plugin):
    hls_re = re.compile(r'''src="(http.*m3u8)"''')

    hls_schema = validate.Schema(
        validate.transform(hls_re.search),
        validate.any(None, validate.all(validate.get(1), validate.url()))
    )

    def _get_streams(self):
        hls_url = self.session.http.get(self.url, schema=self.hls_schema)

        if hls_url:
            return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = TV360
