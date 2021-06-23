import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HDSStream, HLSStream, HTTPStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?bloomberg\.com/
    (?:
        news/videos/[^/]+/[^/]+
        |
        live/(?P<channel>.+)/?
    )
""", re.VERBOSE))
class Bloomberg(Plugin):
    LIVE_API_URL = "https://cdn.gotraffic.net/projector/latest/assets/config/config.min.json?v=1"
    VOD_API_URL = "https://www.bloomberg.com/api/embed?id={0}"

    _re_preload_state = re.compile(r'<script>\s*window.__PRELOADED_STATE__\s*=\s*({.+});?\s*</script>')
    _re_mp4_bitrate = re.compile(r'.*_(?P<bitrate>[0-9]+)\.mp4')

    _schema_url = validate.all(
        {"url": validate.url()},
        validate.get("url")
    )

    _schema_live_list = validate.Schema(
        validate.transform(parse_json),
        validate.get("live"),
        validate.get("channels"),
        validate.get("byChannelId"),
        {
            str: validate.all({"liveId": str}, validate.get("liveId"))
        }
    )
    _schema_live_streams = validate.Schema(
        validate.get("livestreams"),
        {
            str: {
                validate.optional("cdns"): validate.all(
                    [
                        validate.all({"streams": [_schema_url]}, validate.get("streams"))
                    ],
                    validate.transform(lambda x: [i for y in x for i in y])
                )
            }
        }
    )

    _schema_vod_list = validate.Schema(
        validate.transform(parse_json),
        validate.any(
            validate.all(
                {"video": {"videoList": list}},
                validate.get("video"),
                validate.get("videoList")
            ),
            validate.all(
                {"quicktakeVideo": {"videoStory": dict}},
                validate.get("quicktakeVideo"),
                validate.get("videoStory"),
                validate.transform(lambda x: [x])
            )
        ),
        [
            {
                "slug": str,
                "video": validate.all({"bmmrId": str}, validate.get("bmmrId"))
            }
        ]
    )
    _schema_vod_streams = validate.Schema(
        {
            "secureStreams": validate.all([_schema_url]),
            "streams": validate.all([_schema_url])
        },
        validate.transform(lambda x: list(set(x["secureStreams"] + x["streams"])))
    )

    _headers = {
        "authority": "www.bloomberg.com",
        "upgrade-insecure-requests": "1",
        "dnt": "1",
        "accept": ";".join([
            "text/html,application/xhtml+xml,application/xml",
            "q=0.9,image/webp,image/apng,*/*",
            "q=0.8,application/signed-exchange",
            "v=b3"
        ])
    }

    def _get_live_streams(self, channel):
        res = self.session.http.get(self.url, headers=self._headers)
        if "Are you a robot?" in res.text:
            log.error("Are you a robot?")

        match = self._re_preload_state.search(res.text)
        if match is None:
            return

        live_ids = self._schema_live_list.validate(match.group(1))
        live_id = live_ids.get(channel)
        if not live_id:
            log.error(f"Could not find liveId for channel '{channel}'")
            return

        log.debug(f"Found liveId: {live_id}")
        res = self.session.http.get(self.LIVE_API_URL)
        streams = self.session.http.json(res, schema=self._schema_live_streams)
        data = streams.get(live_id, {})

        return data.get("cdns")

    def _get_vod_streams(self):
        res = self.session.http.get(self.url, headers=self._headers)

        match = self._re_preload_state.search(res.text)
        if match is None:
            return

        videos = self._schema_vod_list.validate(match.group(1))
        video_id = next((v["video"] for v in videos if v["slug"] in self.url), None)
        if video_id is None:
            return

        log.debug(f"Found videoId: {video_id}")
        res = self.session.http.get(self.VOD_API_URL.format(video_id), headers=self._headers)
        streams = self.session.http.json(res, schema=self._schema_vod_streams)

        return streams

    def _get_streams(self):
        channel = self.match.group("channel")

        self.session.http.headers.update({"User-Agent": useragents.CHROME})
        if channel:
            streams = self._get_live_streams(channel) or []
        else:
            streams = self._get_vod_streams() or []

        for video_url in streams:
            log.debug(f"Found stream: {video_url}")
            parsed = urlparse(video_url)
            if parsed.path.endswith(".f4m"):
                yield from HDSStream.parse_manifest(self.session, video_url).items()
            elif parsed.path.endswith(".m3u8"):
                yield from HLSStream.parse_variant_playlist(self.session, video_url).items()
            elif parsed.path.endswith(".mp4"):
                match = self._re_mp4_bitrate.match(video_url)
                bitrate = "vod" if match is None else f"{match.group('bitrate')}k"
                yield bitrate, HTTPStream(self.session, video_url)


__plugin__ = Bloomberg
