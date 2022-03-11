"""
$description Live TV channel and video on-demand service run by the International Olympic Committee.
$url olympicchannel.com
$url olympics.com
$type live, vod
$notes Only non-premium content is available
"""

import logging
import re
from html import unescape as html_unescape
from time import time
from urllib.parse import urljoin, urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(\w+\.)?(?:olympics|olympicchannel)\.com/(?:[\w-]+/)?../.+"
))
class OlympicChannel(Plugin):
    _token_api_path = "/tokenGenerator?url={url}&domain={netloc}&_ts={time}"
    _api_schema = validate.Schema(
        validate.parse_json(),
        [{
            validate.optional("src"): validate.url(),
            validate.optional("srcType"): "HLS",
        }],
        validate.transform(lambda v: v[0].get("src")),
    )
    _data_url_re = re.compile(r'data-content-url="([^"]+)"')
    _data_content_re = re.compile(r'data-d3vp-plugin="THEOplayer"\s*data-content="([^"]+)"')
    _data_content_schema = validate.Schema(
        validate.any(
            validate.all(
                validate.transform(_data_url_re.search),
                validate.any(None, validate.get(1)),
            ),
            validate.all(
                validate.transform(_data_content_re.search),
                validate.any(None, validate.get(1)),
            ),
        ),
        validate.any(None, validate.transform(html_unescape)),
    )
    _stream_schema = validate.Schema(
        validate.parse_json(),
        validate.url(),
    )

    def _get_streams(self):
        api_url = self.session.http.get(self.url, schema=self._data_content_schema)
        if api_url and (api_url.startswith("/") or api_url.startswith("http")):
            api_url = urljoin(self.url, api_url)
            stream_url = self.session.http.get(api_url, schema=self._api_schema, headers={"Referer": self.url})
        elif api_url and api_url.startswith("[{"):
            stream_url = self._api_schema.validate(api_url)
        else:
            return

        parsed = urlparse(stream_url)
        api_url = urljoin(self.url, self._token_api_path.format(url=stream_url,
                          netloc="{0}://{1}".format(parsed.scheme, parsed.netloc), time=int(time())))
        stream_url = self.session.http.get(api_url, schema=self._stream_schema, headers={"Referer": self.url})
        return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = OlympicChannel
