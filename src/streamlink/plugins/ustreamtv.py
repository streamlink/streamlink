"""
$description Global live-streaming and video on-demand platform owned by IBM.
$url ustream.tv
$url video.ibm.com
$type live, vod
"""

import logging
import re
from collections import deque
from datetime import datetime, timedelta
from random import randint
from threading import Event, RLock
from typing import Any, Callable, Deque, Dict, List, NamedTuple, Optional, Union
from urllib.parse import urljoin, urlunparse

from requests import Response

from streamlink.exceptions import PluginError, StreamError
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.plugin.api.websocket import WebsocketClient
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.segmented import SegmentedStreamReader, SegmentedStreamWorker, SegmentedStreamWriter
from streamlink.stream.stream import Stream
from streamlink.utils.parse import parse_json


log = logging.getLogger(__name__)


# TODO: use dataclasses for stream formats after dropping py36 to be able to subclass
class StreamFormatVideo(NamedTuple):
    contentType: str
    sourceStreamVersion: int
    initUrl: str
    segmentUrl: str
    bitrate: int
    height: int


class StreamFormatAudio(NamedTuple):
    contentType: str
    sourceStreamVersion: int
    initUrl: str
    segmentUrl: str
    bitrate: int
    language: str = ""


class Segment(NamedTuple):
    num: int
    duration: int
    available_at: datetime
    hash: str
    path: str

    # the segment URLs depend on the CDN and the chosen stream format and its segment template string
    def url(self, base: Optional[str], template: str) -> str:
        return urljoin(
            base or "",
            f"{self.path}/{template.replace('%', str(self.num), 1).replace('%', self.hash, 1)}"
        )


class UStreamTVWsClient(WebsocketClient):
    API_URL = "wss://r{0}-1-{1}-{2}-ws-{3}.ums.services.video.ibm.com/1/ustream"
    APP_ID = 3
    APP_VERSION = 2

    STREAM_OPENED_TIMEOUT = 6

    _schema_cmd = validate.Schema({
        "cmd": str,
        "args": [{str: object}],
    })
    _schema_stream_formats = validate.Schema({
        "streams": [validate.any(
            validate.all(
                {
                    "contentType": "video/mp4",
                    "sourceStreamVersion": int,
                    "initUrl": str,
                    "segmentUrl": str,
                    "bitrate": int,
                    "height": int,
                },
                validate.transform(lambda obj: StreamFormatVideo(**obj))
            ),
            validate.all(
                {
                    "contentType": "audio/mp4",
                    "sourceStreamVersion": int,
                    "initUrl": str,
                    "segmentUrl": str,
                    "bitrate": int,
                    validate.optional("language"): str,
                },
                validate.transform(lambda obj: StreamFormatAudio(**obj))
            ),
            object
        )]
    })
    _schema_stream_segments = validate.Schema({
        "chunkId": int,
        "chunkTime": int,
        "contentAccess": validate.all(
            {
                "accessList": [{
                    "data": {
                        "path": str
                    }
                }]
            },
            validate.get(("accessList", 0, "data", "path"))
        ),
        "hashes": {validate.transform(int): str}
    })

    stream_cdn: Optional[str] = None
    stream_formats_video: Optional[List[StreamFormatVideo]] = None
    stream_formats_audio: Optional[List[StreamFormatAudio]] = None
    stream_initial_id: Optional[int] = None

    def __init__(
        self,
        session,
        media_id,
        application,
        referrer=None,
        cluster="live",
        password=None,
        app_id=APP_ID,
        app_version=APP_VERSION
    ):
        self.opened = Event()
        self.ready = Event()
        self.stream_error = None
        # a list of deques subscribed by worker threads which independently need to read segments
        self.stream_segments_subscribers: List[Deque[Segment]] = []
        self.stream_segments_initial: Deque[Segment] = deque()
        self.stream_segments_lock = RLock()

        self.media_id = media_id
        self.application = application
        self.referrer = referrer
        self.cluster = cluster
        self.password = password
        self.app_id = app_id
        self.app_version = app_version

        super().__init__(session, self._get_url(), origin="https://www.ustream.tv")

    def _get_url(self):
        return self.API_URL.format(randint(0, 0xffffff), self.media_id, self.application, self.cluster)

    def _set_error(self, error: Any):
        self.stream_error = error
        self.ready.set()

    def _set_ready(self):
        if not self.ready.is_set() and self.stream_cdn and self.stream_initial_id is not None:
            self.ready.set()

            if self.opened.wait(self.STREAM_OPENED_TIMEOUT):
                log.debug("Stream opened, keeping websocket connection alive")
            else:
                log.info("Closing websocket connection")
                self.ws.close()

    def segments_subscribe(self) -> Deque[Segment]:
        with self.stream_segments_lock:
            # copy the initial segments deque (segments arrive early)
            new_deque = self.stream_segments_initial.copy()
            self.stream_segments_subscribers.append(new_deque)

            return new_deque

    def _segments_append(self, segment: Segment):
        # if there are no subscribers yet, add segment(s) to the initial deque
        if not self.stream_segments_subscribers:
            self.stream_segments_initial.append(segment)
        else:
            for subscriber_deque in self.stream_segments_subscribers:
                subscriber_deque.append(segment)

    def on_open(self, wsapp):
        args = {
            "type": "viewer",
            "appId": self.app_id,
            "appVersion": self.app_version,
            "rsid": f"{randint(0, 10_000_000_000):x}:{randint(0, 10_000_000_000):x}",
            "rpin": f"_rpin.{randint(0, 1_000_000_000_000_000)}",
            "referrer": self.referrer,
            "clusterHost": "r%rnd%-1-%mediaId%-%mediaType%-%protocolPrefix%-%cluster%.ums.ustream.tv",
            "media": self.media_id,
            "application": self.application
        }
        if self.password:
            args["password"] = self.password

        self.send_json({
            "cmd": "connect",
            "args": [args]
        })

    def on_message(self, wsapp, data: str):
        try:
            parsed = parse_json(data, schema=self._schema_cmd)
        except PluginError:
            log.error(f"Could not parse message: {data[:50]}")
            return

        cmd: str = parsed["cmd"]
        args: List[Dict] = parsed["args"]
        log.trace(f"Received '{cmd}' command")  # type: ignore[attr-defined]
        log.trace(f"{args!r}")  # type: ignore[attr-defined]

        handlers = self._MESSAGE_HANDLERS.get(cmd)
        if handlers is not None:
            for arg in args:
                for name, handler in handlers.items():
                    argdata = arg.get(name)
                    if argdata is not None:
                        log.debug(f"Processing '{cmd}' - '{name}'")
                        handler(self, argdata)

    # noinspection PyMethodMayBeStatic
    def _handle_warning(self, data: Dict):
        log.warning(f"{data['code']}: {str(data['message'])[:50]}")

    # noinspection PyUnusedLocal
    def _handle_reject_nonexistent(self, *args):
        self._set_error("This channel does not exist")

    # noinspection PyUnusedLocal
    def _handle_reject_geo_lock(self, *args):
        self._set_error("This content is not available in your area")

    def _handle_reject_cluster(self, arg: Dict):
        self.cluster = arg["name"]
        log.info(f"Switching cluster to: {self.cluster}")
        self.reconnect(url=self._get_url())

    def _handle_reject_referrer_lock(self, arg: Dict):
        self.referrer = arg["redirectUrl"]
        log.info(f"Updating referrer to: {self.referrer}")
        self.reconnect(url=self._get_url())

    def _handle_module_info_cdn_config(self, data: Dict):
        self.stream_cdn = urlunparse((
            data["protocol"],
            data["data"][0]["data"][0]["sites"][0]["host"],
            data["data"][0]["data"][0]["sites"][0]["path"],
            "", "", ""
        ))
        self._set_ready()

    def _handle_module_info_stream(self, data: Dict):
        if data.get("contentAvailable") is False:
            return self._set_error("This stream is currently offline")

        mp4_segmented = data.get("streamFormats", {}).get("mp4/segmented")
        if not mp4_segmented:
            return

        # parse the stream formats once
        if self.stream_initial_id is None:
            try:
                formats = self._schema_stream_formats.validate(mp4_segmented)
                formats = formats["streams"]
            except PluginError as err:
                return self._set_error(err)
            self.stream_formats_video = list(filter(lambda f: type(f) is StreamFormatVideo, formats))
            self.stream_formats_audio = list(filter(lambda f: type(f) is StreamFormatAudio, formats))

        # parse segment duration and hashes, and queue new segments
        try:
            segmentdata: Dict = self._schema_stream_segments.validate(mp4_segmented)
        except PluginError:
            log.error("Failed parsing hashes")
            return

        current_id: int = segmentdata["chunkId"]
        duration: int = segmentdata["chunkTime"]
        path: str = segmentdata["contentAccess"]
        hashes: Dict[int, str] = segmentdata["hashes"]

        sorted_ids = sorted(hashes.keys())
        count = len(sorted_ids)
        if count == 0:
            return

        # initial segment ID (needed by the workers to filter queued segments)
        if self.stream_initial_id is None:
            self.stream_initial_id = current_id

        current_time = datetime.now()

        # lock the stream segments deques for the worker threads
        with self.stream_segments_lock:
            # interpolate and extrapolate segments from the provided id->hash data
            diff = 10 - sorted_ids[0] % 10  # if there's only one id->hash item, extrapolate until the next decimal
            for idx, segment_id in enumerate(sorted_ids):
                idx_next = idx + 1
                if idx_next < count:
                    # calculate the difference between IDs and use that to interpolate segment IDs
                    # the last id->hash item will use the previous diff to extrapolate segment IDs
                    diff = sorted_ids[idx_next] - segment_id
                for num in range(segment_id, segment_id + diff):
                    self._segments_append(Segment(
                        num=num,
                        duration=duration,
                        available_at=current_time + timedelta(seconds=(num - current_id - 1) * duration / 1000),
                        hash=hashes[segment_id],
                        path=path
                    ))

        self._set_ready()

    # ----

    _MESSAGE_HANDLERS: Dict[str, Dict[str, Callable[["UStreamTVWsClient", Any], None]]] = {
        "warning": {
            "code": _handle_warning,
        },
        "reject": {
            "cluster": _handle_reject_cluster,
            "referrerLock": _handle_reject_referrer_lock,
            "nonexistent": _handle_reject_nonexistent,
            "geoLock": _handle_reject_geo_lock,
        },
        "moduleInfo": {
            "cdnConfig": _handle_module_info_cdn_config,
            "stream": _handle_module_info_stream,
        }
    }


class UStreamTVStreamWriter(SegmentedStreamWriter):
    reader: "UStreamTVStreamReader"
    stream: "UStreamTVStream"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._has_init = False

    def put(self, segment):
        if self.closed:  # pragma: no cover
            return

        if segment is None:
            self.queue(None, None)
        else:
            if not self._has_init:
                self._has_init = True
                self.queue(segment, self.executor.submit(self.fetch, segment, True))
            self.queue(segment, self.executor.submit(self.fetch, segment, False))

    # noinspection PyMethodOverriding
    def fetch(self, segment: Segment, is_init: bool):  # type: ignore[override]
        if self.closed:  # pragma: no cover
            return

        now = datetime.now()
        if segment.available_at > now:
            time_to_wait = (segment.available_at - now).total_seconds()
            log.debug(f"Waiting for {self.stream.kind} segment: {segment.num} ({time_to_wait:.01f}s)")
            if not self.reader.worker.wait(time_to_wait):
                return

        try:
            return self.session.http.get(
                segment.url(
                    self.stream.wsclient.stream_cdn,
                    self.stream.stream_format.initUrl if is_init else self.stream.stream_format.segmentUrl
                ),
                timeout=self.timeout,
                retries=self.retries,
                exception=StreamError
            )
        except StreamError as err:
            log.error(f"Failed to fetch {self.stream.kind} segment {segment.num}: {err}")

    def write(self, segment: Segment, res: Response, *data):
        if self.closed:  # pragma: no cover
            return
        try:
            for chunk in res.iter_content(8192):
                self.reader.buffer.write(chunk)
            log.debug(f"Download of {self.stream.kind} segment {segment.num} complete")
        except OSError as err:
            log.error(f"Failed to read {self.stream.kind} segment {segment.num}: {err}")


class UStreamTVStreamWorker(SegmentedStreamWorker):
    reader: "UStreamTVStreamReader"
    writer: "UStreamTVStreamWriter"
    stream: "UStreamTVStream"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wsclient = self.stream.wsclient
        self.segment_id = self.wsclient.stream_initial_id
        self.queue = self.wsclient.segments_subscribe()

    def iter_segments(self):
        duration = 5000
        while not self.closed:
            try:
                with self.wsclient.stream_segments_lock:
                    segment = self.queue.popleft()
                    duration = segment.duration
            except IndexError:
                # wait for new segments to be queued (half the last segment's duration in seconds)
                if self.wait(duration / 1000 / 2):
                    continue

            if self.closed:
                return

            if segment.num < self.segment_id:
                continue

            log.debug(f"Adding {self.stream.kind} segment {segment.num} to queue")
            yield segment
            self.segment_id = segment.num + 1


class UStreamTVStreamReader(SegmentedStreamReader):
    __worker__ = UStreamTVStreamWorker
    __writer__ = UStreamTVStreamWriter

    stream: "UStreamTVStream"
    worker: "UStreamTVStreamWorker"
    writer: "UStreamTVStreamWriter"

    def open(self):
        self.stream.wsclient.opened.set()
        super().open()

    def close(self):
        super().close()
        self.stream.wsclient.close()


class UStreamTVStream(Stream):
    __shortname__ = "ustreamtv"

    def __init__(
        self,
        session,
        kind: str,
        wsclient: UStreamTVWsClient,
        stream_format: Union[StreamFormatVideo, StreamFormatAudio]
    ):
        super().__init__(session)
        self.kind = kind
        self.wsclient = wsclient
        self.stream_format = stream_format

    def open(self):
        reader = UStreamTVStreamReader(self)
        reader.open()

        return reader


@pluginmatcher(re.compile(r"""
    https?://(?:(?:www\.)?ustream\.tv|video\.ibm\.com)
    (?:
        /combined-embed
        /(?P<combined_channel_id>\d+)
        (?:/video/(?P<combined_video_id>\d+))?
        |
        (?:(?:/embed/|/channel/(?:id/)?)(?P<channel_id>\d+))?
        (?:(?:/embed)?/recorded/(?P<video_id>\d+))?
    )
""", re.VERBOSE))
@pluginargument(
    "password",
    sensitive=True,
    argument_name="ustream-password",
    metavar="PASSWORD",
    help="A password to access password protected UStream.tv channels.",
)
class UStreamTV(Plugin):
    STREAM_READY_TIMEOUT = 15

    def _get_media_app(self):
        video_id = self.match.group("video_id") or self.match.group("combined_video_id")
        if video_id:
            return video_id, "recorded"

        channel_id = self.match.group("channel_id") or self.match.group("combined_channel_id")
        if not channel_id:
            channel_id = self.session.http.get(
                self.url,
                headers={"User-Agent": useragents.CHROME},
                schema=validate.Schema(
                    validate.parse_html(),
                    validate.xml_xpath_string(".//meta[@name='ustream:channel_id'][@content][1]/@content")
                )
            )

        return channel_id, "channel"

    def _get_streams(self):
        if not MuxedStream.is_usable(self.session):
            return

        media_id, application = self._get_media_app()
        if not media_id:
            return

        wsclient = UStreamTVWsClient(
            self.session,
            media_id,
            application,
            referrer=self.url,
            cluster="live",
            password=self.get_option("password")
        )
        log.debug(
            f"Connecting to UStream API:"
            f" media_id={media_id},"
            f" application={application},"
            f" referrer={self.url},"
            f" cluster=live"
        )
        wsclient.start()

        log.debug(f"Waiting for stream data (for at most {self.STREAM_READY_TIMEOUT} seconds)...")
        if (
            not wsclient.ready.wait(self.STREAM_READY_TIMEOUT)
            or not wsclient.is_alive()
            or wsclient.stream_error
        ):
            log.error(wsclient.stream_error or "Waiting for stream data timed out.")
            wsclient.close()
            return

        if not wsclient.stream_formats_audio:
            for video in wsclient.stream_formats_video:
                yield f"{video.height}p", UStreamTVStream(self.session, "video", wsclient, video)
        else:
            for video in wsclient.stream_formats_video:
                for audio in wsclient.stream_formats_audio:
                    yield f"{video.height}p+a{audio.bitrate}k", MuxedStream(
                        self.session,
                        UStreamTVStream(self.session, "video", wsclient, video),
                        UStreamTVStream(self.session, "audio", wsclient, audio)
                    )


__plugin__ = UStreamTV
