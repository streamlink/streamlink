"""
$description Live TV channels from RAI, an Italian public, state-owned broadcaster.
$url raiplay.it
$type live
$region Italy
"""

import logging
import re
from urllib.parse import urlparse, urlunparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


class RaiPlayHLSStream(HLSStream):
    @classmethod
    def _get_variant_playlist(cls, res):
        res.encoding = "UTF-8"
        return super()._get_variant_playlist(res)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?raiplay\.it/dirette/(\w+)/?"
))
class RaiPlay(Plugin):
    _re_data = re.compile(r"data-video-json\s*=\s*\"([^\"]+)\"")
    _schema_data = validate.Schema(
        validate.transform(_re_data.search),
        validate.any(None, validate.get(1))
    )
    _schema_json = validate.Schema(
        validate.parse_json(),
        validate.get("video"),
        validate.get("content_url"),
        validate.url()
    )

    def _get_streams(self):
        json_url = self.session.http.get(self.url, schema=self._schema_data)
        if not json_url:
            return

        json_url = urlunparse(urlparse(self.url)._replace(path=json_url))
        log.debug("Found JSON URL: {0}".format(json_url))

        stream_url = self.session.http.get(json_url, schema=self._schema_json)
        log.debug("Found stream URL: {0}".format(stream_url))

        res = self.session.http.request("HEAD", stream_url)
        # status code will be 200 even if geo-blocked, so check the returned content-type
        if not res or not res.headers or res.headers["Content-Type"] == "video/mp4":
            log.error("Geo-restricted content")
            return

        yield from RaiPlayHLSStream.parse_variant_playlist(self.session, stream_url).items()


__plugin__ = RaiPlay
