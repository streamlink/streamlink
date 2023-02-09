"""
$description Live TV channels and video on-demand service from TV4, a Swedish free-to-air broadcaster.
$url tv4play.se
$url fotbollskanalen.se
$type live, vod
$region Sweden
$notes Only non-premium streams are supported
"""

import logging
import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (?:
        tv4play\.se/program/[^?/]+/[^?/]+
        |
        fotbollskanalen\.se/video
    )
    /(?P<video_id>\d+)
""", re.VERBOSE))
class TV4Play(Plugin):
    video_id = None

    api_url = "https://playback-api.b17g.net"
    api_assets = urljoin(api_url, "/asset/{0}")

    _meta_schema = validate.Schema(
        {
            "metadata": {
                "title": str,
            },
            "mediaUri": str,
        },
    )

    @property
    def get_video_id(self):
        if self.video_id is None:
            self.video_id = self.match.group("video_id")
            log.debug("Found video ID: {0}".format(self.video_id))
        return self.video_id

    def get_metadata(self):
        params = {
            "device": "browser",
            "protocol": "hls",
            "service": "tv4",
        }
        try:
            res = self.session.http.get(
                self.api_assets.format(self.get_video_id),
                params=params,
            )
        except Exception as e:
            if "404 Client Error" in str(e):
                raise PluginError("This Video is not available")
            raise e
        log.debug("Found metadata")
        metadata = self.session.http.json(res, schema=self._meta_schema)
        self.title = metadata["metadata"]["title"]
        return metadata

    def get_title(self):
        if self.title is None:
            self.get_metadata()
        return self.title

    def _get_streams(self):
        metadata = self.get_metadata()

        try:
            res = self.session.http.get(urljoin(self.api_url, metadata["mediaUri"]))
        except Exception as e:
            if "401 Client Error" in str(e):
                raise PluginError("This Video is not available in your country")
            raise e

        log.debug("Found stream data")
        data = self.session.http.json(res)
        hls_url = data["playbackItem"]["manifestUrl"]
        log.debug("URL={0}".format(hls_url))
        yield from HLSStream.parse_variant_playlist(self.session, hls_url).items()


__plugin__ = TV4Play
