"""
$description Live TV channels from RAI, an Italian public, state-owned broadcaster.
$url raiplay.it
$type live
$region Italy
"""

import logging
import re

from streamlink.compat import urlparse, urlunparse
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?raiplay\.it/dirette/(\w+)/?"
))
class RaiPlay(Plugin):
    def _get_streams(self):
        json_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//*[@data-video-json][1]/@data-video-json"),
        ))
        if not json_url:
            return

        json_url = urlunparse(urlparse(self.url)._replace(path=json_url))
        log.debug("Found JSON URL: {0}".format(json_url))

        stream_url = self.session.http.get(json_url, schema=validate.Schema(
            validate.parse_json(),
            {"video": {"content_url": validate.url()}},
            validate.get(("video", "content_url")),
        ))
        log.debug("Found stream URL: {0}".format(stream_url))

        res = self.session.http.request("HEAD", stream_url)
        # status code will be 200 even if geo-blocked, so check the returned content-type
        if not res or not res.headers or res.headers["Content-Type"] == "video/mp4":
            log.error("Geo-restricted content")
            return

        for stream in HLSStream.parse_variant_playlist(self.session, stream_url).items():
            yield stream


__plugin__ = RaiPlay
