"""
$description Global live-streaming and video hosting social platform owned by Google.
$url youtube.com
$url youtu.be
$type live
$metadata id
$metadata author
$metadata category
$metadata title
$notes VOD content and protected videos are not supported
"""

import json
import logging
import re
from urllib.parse import urlparse, urlunparse

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.data import search_dict
from streamlink.utils.parse import parse_json


log = logging.getLogger(__name__)


@pluginmatcher(
    name="default",
    pattern=re.compile(
        r"https?://(?:\w+\.)?youtube\.com/(?:v/|live/|watch\?(?:.*&)?v=)(?P<video_id>[\w-]{11})",
    ),
)
@pluginmatcher(
    name="channel",
    pattern=re.compile(
        r"https?://(?:\w+\.)?youtube\.com/(?:@|c(?:hannel)?/|user/)?(?P<channel>[^/?]+)(?P<live>/live)?/?$",
    ),
)
@pluginmatcher(
    name="embed",
    pattern=re.compile(
        r"https?://(?:\w+\.)?youtube\.com/embed/(?:live_stream\?channel=(?P<live>[^/?&]+)|(?P<video_id>[\w-]{11}))",
    ),
)
@pluginmatcher(
    name="shorthand",
    pattern=re.compile(
        r"https?://youtu\.be/(?P<video_id>[\w-]{11})",
    ),
)
class YouTube(Plugin):
    _re_ytInitialData = re.compile(r"""var\s+ytInitialData\s*=\s*({.*?})\s*;\s*</script>""", re.DOTALL)
    _re_ytInitialPlayerResponse = re.compile(r"""var\s+ytInitialPlayerResponse\s*=\s*({.*?});\s*var\s+\w+\s*=""", re.DOTALL)

    _url_canonical = "https://www.youtube.com/watch?v={video_id}"
    _url_channelid_live = "https://www.youtube.com/channel/{channel_id}/live"

    # There are missing itags
    adp_video = {
        137: "1080p",
        299: "1080p60",  # HFR
        264: "1440p",
        308: "1440p60",  # HFR
        266: "2160p",
        315: "2160p60",  # HFR
        138: "2160p",
        302: "720p60",  # HFR
        135: "480p",
        133: "240p",
        160: "144p",
    }
    adp_audio = {
        140: 128,
        141: 256,
        171: 128,
        249: 48,
        250: 64,
        251: 160,
        256: 256,
        258: 258,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parsed = urlparse(self.url)

        # translate input URLs to be able to find embedded data and to avoid unnecessary HTTP redirects
        if parsed.netloc == "gaming.youtube.com":
            self.url = urlunparse(parsed._replace(scheme="https", netloc="www.youtube.com"))
        elif self.matches["shorthand"]:
            self.url = self._url_canonical.format(video_id=self.match["video_id"])
        elif self.matches["embed"] and self.match["video_id"]:
            self.url = self._url_canonical.format(video_id=self.match["video_id"])
        elif self.matches["embed"] and self.match["live"]:
            self.url = self._url_channelid_live.format(channel_id=self.match["live"])
        elif parsed.scheme != "https":
            self.url = urlunparse(parsed._replace(scheme="https"))

        self.session.http.headers.update({"User-Agent": useragents.CHROME})

    @classmethod
    def stream_weight(cls, stream):
        match_3d = re.match(r"(\w+)_3d", stream)
        match_hfr = re.match(r"(\d+p)(\d+)", stream)
        if match_3d:
            weight, group = Plugin.stream_weight(match_3d.group(1))
            weight -= 1
            group = "youtube_3d"
        elif match_hfr:
            weight, group = Plugin.stream_weight(match_hfr.group(1))
            weight += 1
            group = "high_frame_rate"
        else:
            weight, group = Plugin.stream_weight(stream)

        return weight, group

    @staticmethod
    def _schema_consent(data):
        schema_consent = validate.Schema(
            validate.parse_html(),
            validate.any(
                validate.xml_find(".//form[@action='https://consent.youtube.com/s']"),
                validate.all(
                    validate.xml_xpath(".//form[@action='https://consent.youtube.com/save']"),
                    validate.filter(lambda elem: elem.xpath(".//input[@type='hidden'][@name='set_ytc'][@value='true']")),
                    validate.get(0),
                ),
            ),
            validate.union((
                validate.get("action"),
                validate.xml_xpath(".//input[@type='hidden']"),
            )),
        )
        return schema_consent.validate(data)

    def _schema_canonical(self, data):
        schema_canonical = validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//link[@rel='canonical'][1]/@href"),
            validate.regex(self.matchers["default"].pattern),
            validate.get("video_id"),
        )
        return schema_canonical.validate(data)

    @classmethod
    def _schema_playabilitystatus(cls, data):
        schema = validate.Schema(
            {
                "playabilityStatus": {
                    "status": str,
                    validate.optional("reason"): validate.any(str, None),
                },
            },
            validate.get("playabilityStatus"),
            validate.union_get("status", "reason"),
        )
        return schema.validate(data)

    @classmethod
    def _schema_videodetails(cls, data):
        schema = validate.Schema(
            {
                "videoDetails": {
                    "videoId": str,
                    "author": str,
                    "title": str,
                    validate.optional("isLive"): validate.transform(bool),
                    validate.optional("isLiveContent"): validate.transform(bool),
                    validate.optional("isLiveDvrEnabled"): validate.transform(bool),
                    validate.optional("isLowLatencyLiveStream"): validate.transform(bool),
                    validate.optional("isPrivate"): validate.transform(bool),
                },
                "microformat": validate.all(
                    validate.any(
                        validate.all(
                            {"playerMicroformatRenderer": dict},
                            validate.get("playerMicroformatRenderer"),
                        ),
                        validate.all(
                            {"microformatDataRenderer": dict},
                            validate.get("microformatDataRenderer"),
                        ),
                    ),
                    {
                        "category": str,
                    },
                ),
            },
            validate.union_get(
                ("videoDetails", "videoId"),
                ("videoDetails", "author"),
                ("microformat", "category"),
                ("videoDetails", "title"),
                ("videoDetails", "isLive"),
            ),
        )
        videoDetails = schema.validate(data)
        log.trace(f"videoDetails = {videoDetails!r}")
        return videoDetails

    @classmethod
    def _schema_streamingdata(cls, data):
        schema = validate.Schema(
            {
                "streamingData": {
                    validate.optional("hlsManifestUrl"): str,
                    validate.optional("formats"): [
                        validate.all(
                            {
                                "itag": int,
                                "qualityLabel": str,
                                validate.optional("url"): validate.url(scheme="http"),
                            },
                            validate.union_get("url", "qualityLabel"),
                        ),
                    ],
                    validate.optional("adaptiveFormats"): [
                        validate.all(
                            {
                                "itag": int,
                                "mimeType": validate.all(
                                    str,
                                    validate.regex(
                                        re.compile(r"""^(?P<type>\w+)/(?P<container>\w+); codecs="(?P<codecs>.+)"$"""),
                                    ),
                                    validate.union_get("type", "codecs"),
                                ),
                                validate.optional("url"): validate.url(scheme="http"),
                                validate.optional("qualityLabel"): str,
                            },
                            validate.union_get("url", "qualityLabel", "itag", "mimeType"),
                        ),
                    ],
                },
            },
            validate.get("streamingData"),
            validate.union_get("hlsManifestUrl", "formats", "adaptiveFormats"),
        )
        hls_manifest, formats, adaptive_formats = schema.validate(data)
        return hls_manifest, formats or [], adaptive_formats or []

    def _create_adaptive_streams(self, adaptive_formats):
        streams = {}
        adaptive_streams = {}
        audio_streams = {}
        best_audio_itag = None

        # Extract audio streams from the adaptive format list
        for url, _label, itag, mimeType in adaptive_formats:
            if url is None:
                continue

            # extract any high quality streams only available in adaptive formats
            adaptive_streams[itag] = url
            stream_type, stream_codec = mimeType
            stream_codec = re.sub(r"^(\w+).*$", r"\1", stream_codec)

            if stream_type == "audio" and itag in self.adp_audio:
                audio_bitrate = self.adp_audio[itag]
                if stream_codec not in audio_streams or audio_bitrate > self.adp_audio[audio_streams[stream_codec]]:
                    audio_streams[stream_codec] = itag

                # find the best quality audio stream m4a, opus or vorbis
                if best_audio_itag is None or audio_bitrate > self.adp_audio[best_audio_itag]:
                    best_audio_itag = itag

        if (
            not best_audio_itag
            or self.session.http.head(adaptive_streams[best_audio_itag], raise_for_status=False).status_code >= 400
        ):
            return {}

        streams.update({
            f"audio_{stream_codec}": HTTPStream(self.session, adaptive_streams[itag])
            for stream_codec, itag in audio_streams.items()
        })

        if best_audio_itag and adaptive_streams and MuxedStream.is_usable(self.session):
            aurl = adaptive_streams[best_audio_itag]
            for itag, name in self.adp_video.items():
                if itag not in adaptive_streams:
                    continue
                vurl = adaptive_streams[itag]
                log.debug(f"MuxedStream: v {itag} a {best_audio_itag} = {name}")
                streams[name] = MuxedStream(
                    self.session,
                    HTTPStream(self.session, vurl),
                    HTTPStream(self.session, aurl),
                )

        return streams

    def _get_res(self, url):
        res = self.session.http.get(url)
        if urlparse(res.url).netloc == "consent.youtube.com":
            target, elems = self._schema_consent(res.text)
            c_data = {
                elem.attrib.get("name"): elem.attrib.get("value")
                for elem in elems
            }  # fmt: skip
            log.debug(f"consent target: {target}")
            log.debug(f"consent data: {', '.join(c_data.keys())}")
            res = self.session.http.post(target, data=c_data)
        return res

    @staticmethod
    def _get_data_from_regex(res, regex, descr):
        match = re.search(regex, res.text)
        if not match:
            log.debug(f"Missing {descr}")
            return
        return parse_json(match.group(1))

    def _get_data_from_api(self, res):
        try:
            video_id = self.match["video_id"]
        except IndexError:
            video_id = None

        if video_id is None:
            try:
                video_id = self._schema_canonical(res.text)
            except (PluginError, TypeError):
                return

        try:
            api_key = re.search(r'"INNERTUBE_API_KEY":\s*"([^"]+)"', res.text).group(1)
        except AttributeError:
            api_key = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"

        try:
            client_version = re.search(r'"INNERTUBE_CLIENT_VERSION":\s*"([\d\.]+)"', res.text).group(1)
        except AttributeError:
            client_version = "1.20210616.1.0"

        res = self.session.http.post(
            "https://www.youtube.com/youtubei/v1/player",
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            data=json.dumps({
                "videoId": video_id,
                "contentCheckOk": True,
                "racyCheckOk": True,
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": client_version,
                        "platform": "DESKTOP",
                        "clientScreen": "EMBED",
                        "clientFormFactor": "UNKNOWN_FORM_FACTOR",
                        "browserName": "Chrome",
                    },
                    "user": {"lockedSafetyMode": "false"},
                    "request": {"useSsl": "true"},
                },
            }),
        )
        return parse_json(res.text)

    @staticmethod
    def _data_video_id(data):
        if not data:
            return None
        for key in ("videoRenderer", "gridVideoRenderer"):
            for videoRenderer in search_dict(data, key):
                videoId = videoRenderer.get("videoId")
                if videoId is not None:
                    return videoId

    def _data_status(self, data, errorlog=False):
        if not data:
            return False
        status, reason = self._schema_playabilitystatus(data)
        # assume that there's an error if reason is set (status will still be "OK" for some reason)
        if status != "OK" or reason:
            if errorlog:
                log.error(f"Could not get video info - {status}: {reason}")
            return False
        return True

    def _get_streams(self):
        res = self._get_res(self.url)

        if self.matches["channel"] and not self.match["live"]:
            initial = self._get_data_from_regex(res, self._re_ytInitialData, "initial data")
            video_id = self._data_video_id(initial)
            if video_id is None:
                log.error("Could not find videoId on channel page")
                return
            self.url = self._url_canonical.format(video_id=video_id)
            res = self._get_res(self.url)

        data = self._get_data_from_regex(res, self._re_ytInitialPlayerResponse, "initial player response")
        if not self._data_status(data):
            data = self._get_data_from_api(res)
            if not self._data_status(data, True):
                return

        self.id, self.author, self.category, self.title, is_live = self._schema_videodetails(data)
        log.debug(f"Using video ID: {self.id}")

        if is_live:
            log.debug("This video is live.")

        streams = {}
        hls_manifest, formats, adaptive_formats = self._schema_streamingdata(data)

        protected = any(url is None for url, *_ in formats + adaptive_formats)
        if protected:
            log.debug("This video may be protected.")

        for url, label in formats:
            if url is None:
                continue
            if self.session.http.head(url, raise_for_status=False).status_code >= 400:
                break
            streams[label] = HTTPStream(self.session, url)

        if not is_live:
            streams.update(self._create_adaptive_streams(adaptive_formats))

        if hls_manifest:
            streams.update(HLSStream.parse_variant_playlist(self.session, hls_manifest, name_key="pixels"))

        if not streams:
            if protected:
                raise PluginError("This plugin does not support protected videos, try yt-dlp instead")
            if formats or adaptive_formats:
                raise PluginError("This plugin does not support VOD content, try yt-dlp instead")

        return streams


__plugin__ = YouTube
