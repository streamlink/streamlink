"""
$description Global live-streaming and video hosting social platform.
$url vimeo.com
$type live, vod
$metadata id
$metadata author
$metadata title
$notes Password protected streams are not supported
"""

import base64
import re
import time
import xml.etree.ElementTree as ET
from datetime import timedelta
from functools import partial
from urllib.parse import urljoin, urlparse

from isodate import duration_isoformat  # type: ignore[import]

from streamlink.exceptions import NoStreamsError, PluginError
from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import MPD, DASHStream
from streamlink.stream.dash.dash import DASHStreamReader, DASHStreamWriter
from streamlink.stream.ffmpegmux import FFMPEGMuxer, MuxedStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.hls.hls import MuxedHLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.times import now
from streamlink.utils.url import update_scheme


log = getLogger(__name__)


def _calculate_segment_duration(segments: list[dict]) -> int:
    if len(segments) < 2:
        return 6000
    durations = [
        segments[i]["start"] - segments[i - 1]["start"]
        for i in range(1, len(segments))
        if segments[i]["start"] > segments[i - 1]["start"]
    ]
    if not durations:
        return 6000
    return int((sum(durations) / len(durations)) * 1000)


def _create_representation(parent: ET.Element, track: dict) -> None:
    rep = ET.SubElement(parent, "Representation")
    rep.set("id", track["id"])
    rep.set("mimeType", track["mime_type"])
    rep.set("codecs", track["codecs"])
    rep.set("bandwidth", str(track["bitrate"]))
    if track.get("width"):
        rep.set("width", str(track["width"]))
    if track.get("height"):
        rep.set("height", str(track["height"]))
    if track.get("framerate"):
        rep.set("frameRate", str(round(float(track["framerate"]))))

    if track.get("sampleRate"):
        rep.set("audioSamplingRate", str(track["sampleRate"]))

    seg_list = ET.SubElement(rep, "SegmentList")
    seg_list.set("timescale", "1000")
    segments = track.get("segments", [])
    seg_list.set("duration", str(_calculate_segment_duration(segments)))

    init_seg = track.get("init_segment", "")
    if init_seg:
        init_elem = ET.SubElement(seg_list, "Initialization")
        init_elem.set("sourceURL", f"data:{track['mime_type']};base64,{init_seg}")

    track_base = track.get("base_url", "")
    if track_base and not track_base.endswith("/"):
        track_base += "/"
    for segment in segments:
        seg_url = ET.SubElement(seg_list, "SegmentURL")
        seg_url.set("media", f"{track_base}{segment['url']}")


def _add_adaptation_set(parent, tracks, mime_type, set_id):
    if not tracks:
        return
    aset = ET.SubElement(parent, "AdaptationSet")
    aset.set("id", str(set_id))
    aset.set("mimeType", mime_type)
    aset.set("segmentAlignment", "true")
    for track in tracks:
        _create_representation(aset, track)


def json_to_mpd(manifest: dict, playlist_json_url: str) -> tuple:
    base_url = urljoin(playlist_json_url + "/", manifest.get("base_url", ""))

    tracks = manifest.get("video", []) + manifest.get("audio", [])
    durations = [t["duration"] for t in tracks if t.get("duration")]
    max_duration = max(durations) if durations else 0
    max_seg_durations = [t["max_segment_duration"] for t in tracks if t.get("max_segment_duration")]
    min_buffer = max(max_seg_durations) if max_seg_durations else 7

    mpd_element = ET.Element("MPD")
    mpd_element.set("xmlns", "urn:mpeg:dash:schema:mpd:2011")
    mpd_element.set("type", "static")
    mpd_element.set("mediaPresentationDuration", duration_isoformat(timedelta(seconds=max_duration)))
    mpd_element.set("minBufferTime", duration_isoformat(timedelta(seconds=min_buffer)))
    mpd_element.set("profiles", "urn:mpeg:dash:profile:isoff-live:2011")

    period_element = ET.SubElement(mpd_element, "Period")
    period_element.set("id", "0")
    period_element.set("start", "PT0S")
    base_url_elem = ET.SubElement(period_element, "BaseURL")
    base_url_elem.text = base_url

    video_tracks = manifest.get("video", [])
    audio_tracks = manifest.get("audio", [])
    _add_adaptation_set(period_element, video_tracks, "video/mp4", 0)
    _add_adaptation_set(period_element, audio_tracks, "audio/mp4", len(video_tracks))

    mpd = MPD(mpd_element, url=playlist_json_url)
    period_obj = mpd.periods[0]

    video_reps = []
    if video_tracks:
        video_reps = list(period_obj.adaptationSets[0].representations)

    audio_reps = []
    if audio_tracks:
        audio_idx = len(period_obj.adaptationSets) - 1
        audio_reps = list(period_obj.adaptationSets[audio_idx].representations)

    return mpd, video_reps, audio_reps


class VimeoAPI:
    _player_url = "https://player.vimeo.com/video/{video_id}"
    _video_url = "https://vimeo.com/{video_id}"

    def __init__(self, session):
        self.session = session

    @staticmethod
    def _schema_config(config):
        schema_cdns = validate.all(
            {
                "cdns": {
                    str: validate.all(
                        {validate.optional("url"): validate.url()},
                        validate.get("url"),
                    ),
                },
            },
            validate.get("cdns"),
        )
        schema_config = validate.Schema(
            {
                "request": {
                    "files": {
                        validate.optional("hls"): schema_cdns,
                        validate.optional("dash"): schema_cdns,
                        validate.optional("progressive"): [
                            validate.all(
                                {
                                    validate.optional("url"): validate.url(),
                                    "quality": str,
                                },
                                validate.union_get("quality", "url"),
                            ),
                        ],
                    },
                    validate.optional("text_tracks"): [
                        validate.all(
                            {
                                validate.optional("url"): str,
                                "lang": str,
                            },
                            validate.union_get("lang", "url"),
                        ),
                    ],
                },
                validate.optional("video"): validate.none_or_all(
                    {
                        "id": int,
                        "title": str,
                        "owner": {
                            "name": str,
                        },
                    },
                    validate.union_get(
                        "id",
                        ("owner", "name"),
                        "title",
                    ),
                ),
            },
            validate.union_get(
                ("request", "files", "hls"),
                ("request", "files", "dash"),
                ("request", "files", "progressive"),
                ("request", "text_tracks"),
                "video",
            ),
        )
        return schema_config.validate(config)

    def get_player_config(self, video_id):
        res = self.session.http.get(
            self._player_url.format(video_id=video_id),
            acceptable_status=(200, 401, 403),
        )
        if not res.status_code == 200:
            log.warning("Failed to get player config. Status code: %s", res.status_code)
            return None, None

        data = validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//script[contains(text(),'window.playerConfig')][1]/text()"),
            validate.none_or_all(
                re.compile(r"^\s*window\.playerConfig\s*=\s*(?P<json>{.+?})\s*$"),
                validate.none_or_all(
                    validate.get("json"),
                    validate.parse_json(),
                    validate.transform(self._schema_config),
                ),
            ),
        ).validate(res.text)

        signatures = re.compile(r'signature"\s*:\s*"([^"]+)"').findall(res.text)
        signature = next(
            (s for s in signatures if s[-10:].isdigit()),
            None,
        )

        return data, signature

    def get_config_url(self, video_id, signature):

        jwt, api_url = self.session.http.get(
            "https://vimeo.com/_next/viewer",
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "jwt": str,
                    "apiUrl": str,
                },
                validate.union_get("jwt", "apiUrl"),
            ),
        )
        uri = self.session.http.get(
            "https://vimeo.com/api/oembed.json",
            params={"url": self._video_url.format(video_id=video_id)},
            schema=validate.Schema(
                validate.parse_json(),
                {validate.optional("uri"): str},
                validate.get("uri"),
            ),
        )
        if not uri:
            return

        player_config_url = urljoin(update_scheme("https://", api_url), uri)
        params = {"fields": "config_url,embed_player_config_url"}
        if signature:
            params["anon_signature"] = signature
        else:
            params["anon_signature"] = "640c32fc459222466468b00e95c4d6538b58f1409307800ce0cd1eb48201e548_1788248639629"

        return self.session.http.get(
            player_config_url,
            params=params,
            headers={"Authorization": f"jwt {jwt}"},
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    {"config_url": validate.url()},
                    {"embed_player_config_url": validate.url()},
                ),
                validate.get("config_url") or validate.get("embed_player_config_url"),
            ),
        )

    def get_config_url_event(self, event_id):
        return self.session.http.get(
            f"https://vimeo.com/event/{event_id}/embed",
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string('.//script[contains(text(),"var htmlString")][1]/text()'),
                validate.none_or_all(
                    re.compile(r"var htmlString\s*=\s*`(?P<html>.+?)`;", re.DOTALL),
                    validate.none_or_all(
                        validate.get("html"),
                        validate.parse_html(),
                        validate.xml_xpath_string(".//*[@data-config-url][1]/@data-config-url"),
                    ),
                ),
            ),
        )

    def get_stream_data(self, config_url):
        return self.session.http.get(
            config_url,
            schema=validate.Schema(
                validate.parse_json(),
                validate.transform(self._schema_config),
            ),
        )


class _DataResponse:
    def __init__(self, data):
        self.content = data

    def iter_content(self, chunk_size):
        return [self.content]


class VimeoDASHStreamWriter(DASHStreamWriter):
    def fetch(self, segment):
        if segment.uri.startswith("data:"):
            _, encoded = segment.uri.split(",", 1)
            data = base64.b64decode(encoded)
            return _DataResponse(data)

        return super().fetch(segment)


class VimeoDASHStreamReader(DASHStreamReader):
    __writer__ = VimeoDASHStreamWriter


class VimeoDASHStream(DASHStream):
    def open(self):
        video, audio = None, None
        rep_video, rep_audio = self.video_representation, self.audio_representation

        timestamp = now()

        if rep_video:
            video = VimeoDASHStreamReader(self, rep_video, timestamp, name="video")
            log.debug("Opening DASH reader for: %r - %s", rep_video.ident, rep_video.mimeType)

        if rep_audio:
            audio = VimeoDASHStreamReader(self, rep_audio, timestamp, name="audio")
            log.debug("Opening DASH reader for: %r - %s", rep_audio.ident, rep_audio.mimeType)

        if video and audio and FFMPEGMuxer.is_usable(self.session):
            video.open()
            audio.open()
            return FFMPEGMuxer(self.session, video, audio, copyts=True).open()
        elif video:
            video.open()
            return video
        elif audio:
            audio.open()
            return audio


class VimeoHLSStream(HLSStream):
    URL_UPDATE_PERIOD = 600
    URL_UPDATE_FAILED = 30

    def __init__(self, session, url, quality, fetch_url_func, **kwargs):
        super().__init__(session, url, **kwargs)
        self._fetch_url_func = fetch_url_func
        self._quality = quality
        self._url = url
        self._url_expire = time.time() + self.URL_UPDATE_PERIOD

    @property
    def url(self) -> str:
        if time.time() > self._url_expire:
            log.debug("HLS URL expired, re-fetching from Vimeo API")
            try:
                self._url = self._fetch_url_func(self._quality)
                self._url_expire = time.time() + self.URL_UPDATE_PERIOD
                log.debug("The URL was successfully updated: _url_expire=%d", self._url_expire)
            except (PluginError, NoStreamsError, OSError) as e:
                log.debug(
                    "Failed to re-fetch HLS URL: %s; reusing last known URL; Retry in %d sec",
                    e,
                    self.URL_UPDATE_FAILED,
                )
                self._url_expire = time.time() + self.URL_UPDATE_FAILED

        return self._url


@pluginmatcher(
    name="default",
    pattern=re.compile(r"https?://(?:www\.|player\.)?vimeo\.com/(?!event/).*?(?P<video_id>\d+)(?:[?#].*)?$"),
)
@pluginmatcher(
    name="event",
    pattern=re.compile(r"https?://(?:www\.)?vimeo\.com/event/(?P<event_id>\d+)"),
)
class Vimeo(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api = VimeoAPI(self.session)

    def _get_stream_data(self):

        if self.matches["event"]:
            log.debug("Getting event config_url")
            config_url = self.api.get_config_url_event(self.match["event_id"])

        else:
            data, signature = self.api.get_player_config(self.match["video_id"])
            if data:
                return data

            log.debug("Getting config_url")
            config_url = self.api.get_config_url(self.match["video_id"], signature)

        if not config_url:
            log.error("The content is not available")
            raise NoStreamsError

        return self.api.get_stream_data(config_url)

    def _get_hls_url(self, quality, audio_index=None):
        hls, _dash, _progressive, _text_tracks, _metadata = self._get_stream_data()
        hls = hls or {}
        for url in hls.values():
            if not url:
                continue
            streams = HLSStream.parse_variant_playlist(self.session, url)
            if quality not in streams:
                raise NoStreamsError
            stream = streams[quality]
            if isinstance(stream, MuxedHLSStream):
                if audio_index is not None:
                    return stream.substreams[audio_index].args["url"]
                return stream.substreams[0].args["url"]
            return stream.url
        raise NoStreamsError

    def _get_hls_streams(self, url):
        for name, stream in HLSStream.parse_variant_playlist(self.session, url).items():
            if isinstance(stream, MuxedHLSStream):
                video_url = stream.substreams[0].args["url"]
                if len(stream.substreams) > 1:
                    audio_url = stream.substreams[1].args["url"]
                    video_stream = VimeoHLSStream(self.session, video_url, name, self._get_hls_url)
                    audio_stream = VimeoHLSStream(self.session, audio_url, name, partial(self._get_hls_url, audio_index=1))
                    yield name, MuxedStream(self.session, video_stream, audio_stream)
                else:
                    yield name, VimeoHLSStream(self.session, video_url, name, self._get_hls_url)
            else:
                yield name, VimeoHLSStream(self.session, stream.url, name, self._get_hls_url)

    def _get_dash_streams(self, playlist_json_url):
        manifest = self.session.http.get(
            playlist_json_url,
            schema=validate.Schema(
                validate.parse_json(),
            ),
        )
        mpd, video_reps, audio_reps = json_to_mpd(manifest, playlist_json_url)

        if not audio_reps:
            audio_reps = [None]

        for vid in video_reps:
            for aud in audio_reps:
                stream = VimeoDASHStream(self.session, mpd, vid, aud)
                name = f"{vid.height}p" if vid.height else f"{vid.bandwidth_rounded:.0f}k"
                if aud and len(audio_reps) > 1:
                    name += f"+a{aud.bandwidth:.0f}k"
                yield name, stream

    def _get_streams(self):
        data = self._get_stream_data()
        if not data:
            return

        hls, dash, progressive, text_tracks, metadata = data
        if metadata:
            self.id, self.author, self.title = metadata

        streams = []
        hls = hls or {}
        for url in hls.values():
            if not url:
                continue
            streams.extend(self._get_hls_streams(url))
            break

        dash = dash or {}
        for url in dash.values():
            if not url or not urlparse(url).path.endswith("playlist.json"):
                continue
            streams.extend(self._get_dash_streams(url))
            break

        streams.extend(
            (quality, HTTPStream(self.session, url)) for quality, url in progressive or [] if url and quality not in streams
        )

        if text_tracks and self.session.get_option("mux-subtitles"):
            substreams = {
                lang: HTTPStream(self.session, urljoin("https://vimeo.com/", url)) for lang, url in text_tracks if url
            }
            for quality, stream in streams:
                yield quality, MuxedStream(self.session, stream, subtitles=substreams)
        else:
            yield from streams


__plugin__ = Vimeo
