"""
$description Live TV channels and video on-demand service from SVT, a Swedish public, state-owned broadcaster.
$url svtplay.se
$type live, vod
$region Sweden
"""

import logging
import re
from urllib.parse import parse_qsl, urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?svtplay\.se/(?P<live>kanaler/)?",
))
class SVTPlay(Plugin):
    _URL_API_VIDEO = "https://api.svt.se/videoplayer-api/video/{item}"
    _MAP_CHANNEL_NAMES = {
        "svt1": "ch-svt1",
        "svt2": "ch-svt2",
        "svtbarn": "ch-barnkanalen",
        "kunskapskanalen": "ch-kunskapskanalen",
        "svt24": "ch-svt24",
    }

    def _api_call(self, item):
        _schema_items = validate.all(
            [
                validate.all(
                    {
                        "format": str,
                        "url": validate.url(),
                    },
                    validate.union_get("format", "url"),
                ),
            ],
            validate.transform(dict),
        )

        self.author, self.title, videos, subtitles = self.session.http.get(
            self._URL_API_VIDEO.format(item=item),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    validate.optional("programTitle"): str,
                    validate.optional("episodeTitle"): str,
                    "videoReferences": _schema_items,
                    validate.optional("subtitleReferences"): _schema_items,
                },
                validate.union_get(
                    "programTitle",
                    "episodeTitle",
                    "videoReferences",
                    "subtitleReferences",
                ),
            ),
        )

        return videos, subtitles

    def _get_live(self):
        live_id = "/".join(urlparse(self.url).path.split("/")[2:])
        if not live_id:
            return

        live_id = self._MAP_CHANNEL_NAMES.get(live_id, f"ch-{live_id}")
        log.debug(f"Live ID={live_id}")
        self.category = "Live"
        videos, subtitles = self._api_call(live_id)

        return self._select_streams(videos, subtitles)

    def _get_vod(self):
        def get_vod_id(url):
            return dict(parse_qsl(urlparse(url).query)).get("id")

        vod_id = get_vod_id(self.url)

        if vod_id is None:
            vod_url = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//*[@data-rt='top-area-play-button'][@href][1]/@href"),
            ))
            if vod_url:
                vod_id = get_vod_id(vod_url)

        if vod_id is None:
            return

        log.debug(f"VOD ID={vod_id}")
        self.category = "Live"
        videos, subtitles = self._api_call(vod_id)

        return self._select_streams(videos, subtitles)

    def _select_streams(self, videos, subtitles):
        # the goal is to have streams with the widest range of qualities/substreams and highest bitrate at the top
        stream_priorities = {
            "dashhbbtv": DASHStream,  # DASH AVC
            "dash-hbbtv-avc": DASHStream,  # DASH AVC
            "dash-avc": DASHStream,  # DASH AVC
            "dash-full": DASHStream,  # DASH AVC
            "dash": DASHStream,  # DASH AVC

            "hlswebvtt": HLSStream,  # HLS with subtitles
            "hls-cmaf-live-vtt": HLSStream,  # HLS with subtitles
            "hls-ts-avc": HLSStream,  # HLS with MPEG-TS
            "hls-ts-full": HLSStream,  # HLS with MPEG-TS
            "hls": HLSStream,  # HLS with MPEG-TS
            "hls-cmaf-live": HLSStream,  # HLS with fMP4
            "hls-cmaf-full": HLSStream,  # HLS with fMP4

            "dash-hbbtv-hevc": DASHStream,  # DASH HEVC (low prio, because of potential user decoder issues)

            "hls-ts-lb-full": HLSStream,  # low bitrate
            "hls-cmaf-lb-full": HLSStream,  # low bitrate
            "dash-lb-full": DASHStream,  # low bitrate
        }

        for fmt, streamtype in stream_priorities.items():
            if fmt not in videos:
                continue

            if streamtype is HLSStream:
                return HLSStream.parse_variant_playlist(self.session, videos[fmt], name_fmt="{pixels}_{bitrate}")

            if streamtype is DASHStream:
                subtitlestreams = {}
                if self.session.get_option("mux-subtitles") and "webvtt" in subtitles:
                    subtitlestreams["webvtt"] = HTTPStream(self.session, subtitles["webvtt"])

                dash_streams = DASHStream.parse_manifest(self.session, videos[fmt])
                if not subtitlestreams:
                    return dash_streams

                return {q: MuxedStream(self.session, s, subtitles=subtitlestreams) for q, s in dash_streams.items()}

    def _get_streams(self):
        if self.match["live"]:
            return self._get_live()
        else:
            return self._get_vod()


__plugin__ = SVTPlay
