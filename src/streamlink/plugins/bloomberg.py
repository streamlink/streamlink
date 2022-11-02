"""
$description America-based television network centred towards business and capital market programming.
$url bloomberg.com
$type live, vod
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?bloomberg\.com/
    (?:
        (?P<live>live)(?:/(?P<channel>[^/]+))?
        |
        news/videos/[^/]+/[^/]+
    )
""", re.VERBOSE))
class Bloomberg(Plugin):
    LIVE_API_URL = "https://cdn.gotraffic.net/projector/latest/assets/config/config.min.json?v=1"
    VOD_API_URL = "https://www.bloomberg.com/api/embed?id={0}"
    DEFAULT_CHANNEL = "us"

    def _get_live_streams(self, data, channel):
        schema_live_ids = validate.Schema(
            {"live": {"channels": {"byChannelId": {
                channel: validate.all(
                    {"liveId": str},
                    validate.get("liveId")
                )
            }}}},
            validate.get(("live", "channels", "byChannelId", channel)),
        )
        try:
            live_id = schema_live_ids.validate(data)
        except PluginError:
            log.error(f"Could not find liveId for channel '{channel}'")
            return

        log.debug(f"Found liveId: {live_id}")
        return self.session.http.get(self.LIVE_API_URL, schema=validate.Schema(
            validate.parse_json(),
            {"livestreams": {
                live_id: {
                    validate.optional("cdns"): validate.all(
                        [{"streams": [{
                            "url": validate.url()
                        }]}],
                        validate.transform(lambda x: [urls["url"] for y in x for urls in y["streams"]])
                    )
                }
            }},
            validate.get(("livestreams", live_id, "cdns"))
        ))

    def _get_vod_streams(self, data):
        schema_vod_list = validate.Schema(
            validate.any(
                validate.all(
                    {"video": {"videoStory": dict}},
                    validate.get(("video", "videoStory"))
                ),
                validate.all(
                    {"quicktakeVideo": {"videoStory": dict}},
                    validate.get(("quicktakeVideo", "videoStory"))
                )
            ),
            {"video": {
                "bmmrId": str
            }},
            validate.get(("video", "bmmrId"))
        )
        schema_url = validate.all(
            {"url": validate.url()},
            validate.get("url")
        )

        try:
            video_id = schema_vod_list.validate(data)
        except PluginError:
            log.error("Could not find videoId")
            return

        log.debug(f"Found videoId: {video_id}")
        vod_url = self.VOD_API_URL.format(video_id)
        secureStreams, streams, self.title = self.session.http.get(vod_url, schema=validate.Schema(
            validate.parse_json(),
            {
                validate.optional("secureStreams"): [schema_url],
                validate.optional("streams"): [schema_url],
                "title": str
            },
            validate.union_get("secureStreams", "streams", "title")
        ))

        return secureStreams or streams

    def _get_streams(self):
        del self.session.http.headers["Accept-Encoding"]

        try:
            data = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'window.__PRELOADED_STATE__')][1]/text()"),
                str,
                validate.regex(re.compile(r"^\s*window\.__PRELOADED_STATE__\s*=\s*({.+})\s*;?\s*$", re.DOTALL)),
                validate.get(1),
                validate.parse_json(),
            ))
        except PluginError:
            log.error("Could not find JSON data. Invalid URL or bot protection...")
            return

        if self.match.group("live"):
            streams = self._get_live_streams(data, self.match.group("channel") or self.DEFAULT_CHANNEL)
        else:
            streams = self._get_vod_streams(data)

        if streams:
            # just return the first stream
            return HLSStream.parse_variant_playlist(self.session, streams[0])


__plugin__ = Bloomberg
