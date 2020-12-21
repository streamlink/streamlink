import logging
import re
from urllib.parse import parse_qsl, urlparse, urlunparse

from streamlink.plugin import Plugin, PluginError
from streamlink.plugin.api import useragents, validate
from streamlink.plugin.api.utils import itertags, parse_query
from streamlink.stream import HLSStream, HTTPStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.utils import parse_json, search_dict

log = logging.getLogger(__name__)


_config_schema = validate.Schema(
    {
        validate.optional("player_response"): validate.all(
            validate.text,
            validate.transform(parse_json),
            {
                validate.optional("streamingData"): {
                    validate.optional("hlsManifestUrl"): validate.text,
                    validate.optional("formats"): [{
                        "itag": int,
                        validate.optional("url"): validate.text,
                        validate.optional("cipher"): validate.text,
                        "qualityLabel": validate.text
                    }],
                    validate.optional("adaptiveFormats"): [{
                        "itag": int,
                        "mimeType": validate.all(
                            validate.text,
                            validate.transform(
                                lambda t:
                                    [t.split(';')[0].split('/')[0], t.split(';')[1].split('=')[1].strip('"')]
                            ),
                            [validate.text, validate.text],
                        ),
                        validate.optional("url"): validate.url(scheme="http"),
                        validate.optional("cipher"): validate.text,
                        validate.optional("signatureCipher"): validate.text,
                        validate.optional("qualityLabel"): validate.text,
                        validate.optional("bitrate"): int
                    }]
                },
                validate.optional("videoDetails"): {
                    validate.optional("isLive"): validate.transform(bool),
                    validate.optional("author"): validate.text,
                    validate.optional("title"): validate.text
                },
                validate.optional("playabilityStatus"): {
                    validate.optional("status"): validate.text,
                    validate.optional("reason"): validate.text
                },
            },
        ),
        "status": validate.text
    }
)

_ytdata_re = re.compile(r'ytInitialData\s*=\s*({.*?});', re.DOTALL)
_url_re = re.compile(r"""(?x)https?://(?:\w+\.)?youtube\.com
    (?:
        (?:
            /(?:
                watch.+v=
                |
                embed/(?!live_stream)
                |
                v/
            )(?P<video_id>[0-9A-z_-]{11})
        )
        |
        (?:
            /(?:
                (?:user|c(?:hannel)?)/
                |
                embed/live_stream\?channel=
            )[^/?&]+
        )
        |
        (?:
            /(?:c/)?[^/?]+/live/?$
        )
    )
""")


class YouTube(Plugin):
    _oembed_url = "https://www.youtube.com/oembed"
    _video_info_url = "https://youtube.com/get_video_info"

    _oembed_schema = validate.Schema(
        {
            "author_name": validate.text,
            "title": validate.text
        }
    )

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

    def __init__(self, url):
        super().__init__(url)
        parsed = urlparse(self.url)
        if parsed.netloc == 'gaming.youtube.com':
            self.url = urlunparse(parsed._replace(netloc='www.youtube.com'))

        self.author = None
        self.title = None
        self.video_id = None
        self.session.http.headers.update({'User-Agent': useragents.CHROME})

    def get_author(self):
        if self.author is None:
            self.get_oembed
        return self.author

    def get_title(self):
        if self.title is None:
            self.get_oembed
        return self.title

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

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

    @property
    def get_oembed(self):
        if self.video_id is None:
            self.video_id = self._find_video_id(self.url)

        params = {
            "url": "https://www.youtube.com/watch?v={0}".format(self.video_id),
            "format": "json"
        }
        res = self.session.http.get(self._oembed_url, params=params)
        data = self.session.http.json(res, schema=self._oembed_schema)
        self.author = data["author_name"]
        self.title = data["title"]

    def _create_adaptive_streams(self, info, streams):
        adaptive_streams = {}
        best_audio_itag = None

        # Extract audio streams from the adaptive format list
        streaming_data = info.get("player_response", {}).get("streamingData", {})
        for stream_info in streaming_data.get("adaptiveFormats", []):
            if "url" not in stream_info:
                continue
            stream_params = dict(parse_qsl(stream_info["url"]))
            if "itag" not in stream_params:
                continue
            itag = int(stream_params["itag"])
            # extract any high quality streams only available in adaptive formats
            adaptive_streams[itag] = stream_info["url"]

            stream_type, stream_format = stream_info["mimeType"]

            if stream_type == "audio":
                stream = HTTPStream(self.session, stream_info["url"])
                name = "audio_{0}".format(stream_format)
                streams[name] = stream

                # find the best quality audio stream m4a, opus or vorbis
                if best_audio_itag is None or self.adp_audio[itag] > self.adp_audio[best_audio_itag]:
                    best_audio_itag = itag

        if best_audio_itag and adaptive_streams and MuxedStream.is_usable(self.session):
            aurl = adaptive_streams[best_audio_itag]
            for itag, name in self.adp_video.items():
                if itag in adaptive_streams:
                    vurl = adaptive_streams[itag]
                    log.debug("MuxedStream: v {video} a {audio} = {name}".format(
                        audio=best_audio_itag,
                        name=name,
                        video=itag,
                    ))
                    streams[name] = MuxedStream(self.session,
                                                HTTPStream(self.session, vurl),
                                                HTTPStream(self.session, aurl))

        return streams

    def _find_video_id(self, url):

        m = _url_re.match(url)
        if m.group("video_id"):
            log.debug("Video ID from URL")
            return m.group("video_id")

        res = self.session.http.get(url)
        datam = _ytdata_re.search(res.text)
        if datam:
            data = parse_json(datam.group(1))
            # find the videoRenderer object, where there is a LVE NOW badge
            for vid_ep in search_dict(data, 'currentVideoEndpoint'):
                video_id = vid_ep.get("watchEndpoint", {}).get("videoId")
                if video_id:
                    log.debug("Video ID from currentVideoEndpoint")
                    return video_id
            for x in search_dict(data, 'videoRenderer'):
                if x.get("viewCountText", {}).get("runs"):
                    if x.get("videoId"):
                        log.debug("Video ID from videoRenderer (live)")
                        return x["videoId"]
                for bstyle in search_dict(x.get("badges", {}), "style"):
                    if bstyle == "BADGE_STYLE_TYPE_LIVE_NOW":
                        if x.get("videoId"):
                            log.debug("Video ID from videoRenderer (live)")
                            return x["videoId"]

        if urlparse(url).path.endswith(("/embed/live_stream", "/live")):
            for link in itertags(res.text, "link"):
                if link.attributes.get("rel") == "canonical":
                    canon_link = link.attributes.get("href")
                    if canon_link != url:
                        if canon_link.endswith("v=live_stream"):
                            log.debug("The video is not available")
                            break
                        else:
                            log.debug("Re-directing to canonical URL: {0}".format(canon_link))
                            return self._find_video_id(canon_link)

        raise PluginError("Could not find a video on this page")

    def _get_stream_info(self, video_id):
        # normal
        _params_1 = {"el": "detailpage"}
        # age restricted
        _params_2 = {"el": "embedded"}
        # embedded restricted
        _params_3 = {"eurl": "https://youtube.googleapis.com/v/{0}".format(video_id)}

        count = 0
        info_parsed = None
        for _params in (_params_1, _params_2, _params_3):
            count += 1
            params = {"video_id": video_id}
            params.update(_params)

            res = self.session.http.get(self._video_info_url, params=params)
            info_parsed = parse_query(res.text, name="config", schema=_config_schema)
            player_response = info_parsed.get("player_response", {})
            playability_status = player_response.get("playabilityStatus", {})
            if (playability_status.get("status") != "OK"):
                reason = playability_status.get("reason")
                log.debug("get_video_info - {0}: {1}".format(
                    count, reason)
                )
                continue
            self.author = player_response.get("videoDetails", {}).get("author")
            self.title = player_response.get("videoDetails", {}).get("title")
            log.debug("get_video_info - {0}: Found data".format(count))
            break

        return info_parsed

    def _get_streams(self):
        is_live = False

        self.video_id = self._find_video_id(self.url)
        log.debug(f"Using video ID: {self.video_id}")

        info = self._get_stream_info(self.video_id)
        if info and info.get("status") == "fail":
            log.error("Could not get video info: {0}".format(info.get("reason")))
            return
        elif not info:
            log.error("Could not get video info")
            return

        if info.get("player_response", {}).get("videoDetails", {}).get("isLive"):
            log.debug("This video is live.")
            is_live = True

        streams = {}
        protected = False
        if (info.get("player_response", {}).get("streamingData", {}).get("adaptiveFormats", [{}])[0].get("cipher")
           or info.get("player_response", {}).get("streamingData", {}).get("adaptiveFormats", [{}])[0].get("signatureCipher")
           or info.get("player_response", {}).get("streamingData", {}).get("formats", [{}])[0].get("cipher")):
            protected = True
            log.debug("This video may be protected.")

        for stream_info in info.get("player_response", {}).get("streamingData", {}).get("formats", []):
            if "url" not in stream_info:
                continue
            stream = HTTPStream(self.session, stream_info["url"])
            name = stream_info["qualityLabel"]

            streams[name] = stream

        if not is_live:
            streams = self._create_adaptive_streams(info, streams)

        hls_manifest = info.get("player_response", {}).get("streamingData", {}).get("hlsManifestUrl")
        if hls_manifest:
            try:
                hls_streams = HLSStream.parse_variant_playlist(
                    self.session, hls_manifest, name_key="pixels"
                )
                streams.update(hls_streams)
            except OSError as err:
                log.warning(f"Failed to extract HLS streams: {err}")

        if not streams and protected:
            raise PluginError("This plugin does not support protected videos, "
                              "try youtube-dl instead")

        return streams


__plugin__ = YouTube
