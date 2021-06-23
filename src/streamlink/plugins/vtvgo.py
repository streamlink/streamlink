import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://vtvgo\.vn/xem-truc-tuyen-kenh-'
))
class VTVgo(Plugin):
    AJAX_URL = 'https://vtvgo.vn/ajax-get-stream'

    _params_re = re.compile(r'''var\s+(?P<key>(?:type_)?id|time|token)\s*=\s*["']?(?P<value>[^"']+)["']?;''')

    _schema_params = validate.Schema(
        validate.transform(lambda html: next(tag.text for tag in itertags(html, "script") if "setplayer(" in tag.text)),
        validate.transform(_params_re.findall),
        [
            ("id", int),
            ("type_id", str),
            ("time", str),
            ("token", str)
        ]
    )
    _schema_stream_url = validate.Schema(
        validate.transform(parse_json),
        {"stream_url": [validate.url()]},
        validate.get("stream_url"),
        validate.get(0)
    )

    def _get_streams(self):
        self.session.http.headers.update({
            'Origin': 'https://vtvgo.vn',
            'Referer': self.url,
            'X-Requested-With': 'XMLHttpRequest',
        })
        params = self.session.http.get(self.url, schema=self._schema_params)

        log.trace('{0!r}'.format(params))
        hls_url = self.session.http.post(self.AJAX_URL, data=dict(params), schema=self._schema_stream_url)

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = VTVgo
