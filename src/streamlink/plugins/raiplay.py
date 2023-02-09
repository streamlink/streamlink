"""
$description Live TV channels from RAI, an Italian public, state-owned broadcaster.
$url raiplay.it
$type live
$region Italy
"""

import logging
import re
from urllib.parse import parse_qsl, urlparse, urlunparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?raiplay\.it/dirette/(\w+)/?",
))
class RaiPlay(Plugin):
    _DEFAULT_MEDIAPOLIS_OUTPUT = "64"

    def _get_streams(self):
        json_url = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//*[@data-video-json][1]/@data-video-json"),
        ))
        if not json_url:
            return

        json_url = urlunparse(urlparse(self.url)._replace(path=json_url))
        log.debug(f"Found JSON URL: {json_url}")

        content_url = self.session.http.get(json_url, schema=validate.Schema(
            validate.parse_json(),
            {"video": {"content_url": validate.url()}},
            validate.get(("video", "content_url")),
        ))
        if not content_url:
            log.error("Missing content URL")
            return

        content_url = content_url.replace("/relinkerServlet.mp4", "/relinkerServlet.htm")
        parsed = urlparse(content_url)
        params = dict(parse_qsl(parsed.query))
        if not parsed.path.endswith(".xml") and not params.get("output"):
            params["output"] = self._DEFAULT_MEDIAPOLIS_OUTPUT
            content_url = update_qsd(urlunparse(parsed), params)

        res = self.session.http.head(content_url)
        # status code will be 200 even if geo-blocked, so check the returned content-type
        if not res or not res.headers or res.headers["Content-Type"] == "video/mp4":
            log.error("Geo-restricted content")
            return

        stream_url = self.session.http.get(
            content_url,
            schema=validate.Schema(
                validate.parse_xml(),
                validate.xml_element(tag="Mediapolis"),
                validate.xml_xpath_string("./url[@type='content']/text()"),
                validate.none_or_all(
                    validate.transform(str.strip),
                    validate.url(path=validate.endswith(".m3u8")),
                ),
            ),
        )
        if not stream_url:
            log.error("Missing stream URL")
            return

        yield from HLSStream.parse_variant_playlist(self.session, stream_url).items()


__plugin__ = RaiPlay
