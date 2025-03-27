from __future__ import annotations

import logging
import re
import struct
from collections.abc import Mapping
from concurrent.futures import Future
from datetime import datetime, timedelta
from typing import Any, ClassVar
from urllib.parse import urlparse

from requests import Response
from requests.exceptions import ChunkedEncodingError, ConnectionError, ContentDecodingError, InvalidSchema  # noqa: A004

from streamlink.buffers import RingBuffer
from streamlink.exceptions import StreamError
from streamlink.session import Streamlink
from streamlink.stream.ffmpegmux import FFMPEGMuxer, MuxedStream
from streamlink.stream.filtered import FilteredStream
from streamlink.stream.hls.m3u8 import M3U8, M3U8Parser, parse_m3u8
from streamlink.stream.hls.segment import ByteRange, HLSPlaylist, HLSSegment, Key, Map, Media
from streamlink.stream.http import HTTPStream
from streamlink.stream.segmented import SegmentedStreamReader, SegmentedStreamWorker, SegmentedStreamWriter
from streamlink.utils.cache import LRUCache
from streamlink.utils.crypto import AES, unpad
from streamlink.utils.formatter import Formatter
from streamlink.utils.l10n import Language
from streamlink.utils.times import now


log = logging.getLogger(".".join(__name__.split(".")[:-1]))


class ByteRangeOffset:
    sequence: int | None = None
    offset: int | None = None

    @staticmethod
    def _calc_end(start: int, size: int) -> int:
        return start + max(size - 1, 0)

    def cached(self, sequence: int, byterange: ByteRange) -> tuple[int, int]:
        if byterange.offset is not None:
            bytes_start = byterange.offset
        elif self.offset is not None and self.sequence == sequence - 1:
            bytes_start = self.offset
        else:
            raise StreamError("Missing BYTERANGE offset")

        bytes_end = self._calc_end(bytes_start, byterange.range)

        self.sequence = sequence
        self.offset = bytes_end + 1

        return bytes_start, bytes_end

    def uncached(self, byterange: ByteRange) -> tuple[int, int]:
        bytes_start = byterange.offset
        if bytes_start is None:
            raise StreamError("Missing BYTERANGE offset")

        return bytes_start, self._calc_end(bytes_start, byterange.range)


class HLSStreamWriter(SegmentedStreamWriter[HLSSegment, Response]):
    WRITE_CHUNK_SIZE = 8192

    reader: HLSStreamReader
    stream: HLSStream

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        options = self.session.options

        self.byterange: ByteRangeOffset = ByteRangeOffset()
        self.map_cache: LRUCache[str, Future] = LRUCache(self.threads)
        self.key_data: bytes | bytearray | memoryview = b""
        self.key_uri: str | None = None
        self.key_uri_override = options.get("hls-segment-key-uri")
        self.stream_data = options.get("hls-segment-stream-data")

        self.ignore_names: re.Pattern | None = None
        ignore_names = {*options.get("hls-segment-ignore-names")}
        if ignore_names:
            segments = "|".join(map(re.escape, ignore_names))
            # noinspection RegExpUnnecessaryNonCapturingGroup
            self.ignore_names = re.compile(rf"(?:{segments})\.ts", re.IGNORECASE)

    @staticmethod
    def num_to_iv(n: int) -> bytes:
        return struct.pack(">8xq", n)

    def create_decryptor(self, key: Key, num: int):
        if key.method != "AES-128":
            raise StreamError(f"Unable to decrypt cipher {key.method}")

        if not self.key_uri_override and not key.uri:
            raise StreamError("Missing URI for decryption key")

        if not self.key_uri_override:
            key_uri = key.uri
        else:
            p = urlparse(key.uri)
            formatter = Formatter({
                "url": lambda: key.uri,
                "scheme": lambda: p.scheme,
                "netloc": lambda: p.netloc,
                "path": lambda: p.path,
                "query": lambda: p.query,
            })
            key_uri = formatter.format(self.key_uri_override)

        if key_uri and self.key_uri != key_uri:
            try:
                res = self.session.http.get(
                    key_uri,
                    exception=StreamError,
                    retries=self.retries,
                    **self.reader.request_params,
                )
            except StreamError as err:
                # FIXME: fix HTTPSession.request()
                original_error = getattr(err, "err", None)
                if isinstance(original_error, InvalidSchema):
                    raise StreamError(f"Unable to find connection adapter for key URI: {key_uri}") from original_error
                raise  # pragma: no cover

            res.encoding = "binary/octet-stream"
            self.key_data = res.content
            self.key_uri = key_uri

        iv = key.iv or self.num_to_iv(num)

        # Pad IV if needed
        iv = b"\x00" * (16 - len(iv)) + iv

        return AES.new(self.key_data, AES.MODE_CBC, iv)

    def create_request_params(self, num: int, segment: HLSSegment | Map, is_map: bool):
        request_params = dict(self.reader.request_params)
        headers = request_params.pop("headers", {})

        if segment.byterange:
            if is_map:
                bytes_start, bytes_end = self.byterange.uncached(segment.byterange)
            else:
                bytes_start, bytes_end = self.byterange.cached(num, segment.byterange)
            headers["Range"] = f"bytes={bytes_start}-{bytes_end}"

        request_params["headers"] = headers

        return request_params

    def put(self, segment: HLSSegment | None):
        if self.closed:
            return

        if segment is None:
            self.queue(None, None)
            return

        # queue segment-map first
        if segment.map is not None:
            # get the cached segment-map, if available
            future = self.map_cache.get(segment.map.uri)
            if future and segment.discontinuity:
                # special case: queue the cached segment map if it's set on a discontinuity segment
                self.queue(segment, future, True)
            elif not future:
                # keep the segment-map in the cache, so we can check whether we've already queued it
                future = self.executor.submit(self.fetch_map, segment)
                self.map_cache.set(segment.map.uri, future)
                self.queue(segment, future, True)

        # regular segment request
        future = self.executor.submit(self.fetch, segment)
        self.queue(segment, future, False)

    def fetch(self, segment: HLSSegment) -> Response | None:
        try:
            return self._fetch(
                segment.uri,
                stream=self.stream_data,
                **self.create_request_params(segment.num, segment, False),
            )
        except StreamError as err:
            log.error(f"Failed to fetch segment {segment.num}: {err}")

    def fetch_map(self, segment: HLSSegment) -> Response | None:
        segment_map: Map = segment.map  # type: ignore[assignment]  # map is not None
        try:
            return self._fetch(
                segment_map.uri,
                stream=False,
                **self.create_request_params(segment.num, segment_map, True),
            )
        except StreamError as err:
            log.error(f"Failed to fetch map for segment {segment.num}: {err}")

    def _fetch(self, url: str, **request_params) -> Response | None:
        if self.closed or not self.retries:  # pragma: no cover
            return None

        return self.session.http.get(
            url,
            timeout=self.timeout,
            retries=self.retries,
            exception=StreamError,
            **request_params,
        )

    def should_filter_segment(self, segment: HLSSegment) -> bool:
        return self.ignore_names is not None and self.ignore_names.search(segment.uri) is not None

    def write(self, segment: HLSSegment, result: Response, *data):
        if not self.should_filter_segment(segment):
            log.debug(f"Writing segment {segment.num} to output")

            written_once = self.reader.buffer.written_once
            try:
                return self._write(segment, result, *data)
            finally:
                is_paused = self.reader.is_paused()

                # Depending on the filtering implementation, the segment's discontinuity attribute can be missing.
                # Also check if the output will be resumed after data has already been written to the buffer before.
                if segment.discontinuity or is_paused and written_once:
                    log.warning(
                        "Encountered a stream discontinuity. This is unsupported and will result in incoherent output data.",
                    )

                # unblock reader thread after writing data to the buffer
                if is_paused:
                    log.info("Resuming stream output")
                    self.reader.resume()

        else:
            log.debug(f"Discarding segment {segment.num}")

            # Read and discard any remaining HTTP response data in the response connection.
            # Unread data in the HTTPResponse connection blocks the connection from being released back to the pool.
            result.raw.drain_conn()

            # block reader thread if filtering out segments
            if not self.reader.is_paused():
                log.info("Filtering out segments and pausing stream output")
                self.reader.pause()

    def _write(self, segment: HLSSegment, result: Response, is_map: bool):
        # TODO: Rewrite HLSSegment, HLSStreamWriter and HLSStreamWorker based on independent initialization section segments,
        #       similar to the DASH implementation
        key = segment.map.key if is_map and segment.map else segment.key
        if key and key.method != "NONE":
            try:
                decryptor = self.create_decryptor(key, segment.num)
            except (StreamError, ValueError) as err:
                log.error(f"Failed to create decryptor: {err}")
                self.close()
                return

            try:
                # Unlike plaintext segments, encrypted segments can't be written to the buffer in small chunks
                # because of the byte padding at the end of the decrypted data, which means that decrypting in
                # smaller chunks is unnecessary if the entire segment needs to be kept in memory anyway, unless
                # we defer the buffer writes by one read call and apply the unpad call only to the last read call.
                encrypted_chunk = result.content
                decrypted_chunk = decryptor.decrypt(encrypted_chunk)
                chunk = unpad(decrypted_chunk, AES.block_size, style="pkcs7")
                self.reader.buffer.write(chunk)
            except (ChunkedEncodingError, ContentDecodingError, ConnectionError) as err:
                log.error(f"Download of segment {segment.num} failed: {err}")
                return
            except ValueError as err:
                log.error(f"Error while decrypting segment {segment.num}: {err}")
                return

        else:
            try:
                for chunk in result.iter_content(self.WRITE_CHUNK_SIZE):
                    self.reader.buffer.write(chunk)
            except (ChunkedEncodingError, ContentDecodingError, ConnectionError) as err:
                log.error(f"Download of segment {segment.num} failed: {err}")
                return

        if is_map:
            log.debug(f"Segment initialization {segment.num} complete")
        else:
            log.debug(f"Segment {segment.num} complete")


class HLSStreamWorker(SegmentedStreamWorker[HLSSegment, Response]):
    reader: HLSStreamReader
    writer: HLSStreamWriter
    stream: HLSStream

    SEGMENT_QUEUE_TIMING_THRESHOLD_MIN = 5.0

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.playlist_changed = False
        self.playlist_end: int | None = None
        self.playlist_targetduration: float = 0
        self.playlist_sequence: int = -1
        self.playlist_sequence_last: datetime = now()
        self.playlist_segments: list[HLSSegment] = []

        self.playlist_reload_last: datetime = now()
        self.playlist_reload_time: float = 6
        self.playlist_reload_time_override = self.session.options.get("hls-playlist-reload-time")
        self.playlist_reload_retries = self.session.options.get("hls-playlist-reload-attempts")
        self.segment_queue_timing_threshold_factor = self.session.options.get("hls-segment-queue-threshold")
        self.live_edge = self.session.options.get("hls-live-edge")
        self.duration_offset_start = int(self.stream.start_offset + (self.session.options.get("hls-start-offset") or 0))
        self.duration_limit = self.stream.duration or (
            int(self.session.options.get("hls-duration")) if self.session.options.get("hls-duration") else None
        )
        self.hls_live_restart = self.stream.force_restart or self.session.options.get("hls-live-restart")

        if str(self.playlist_reload_time_override).isnumeric() and float(self.playlist_reload_time_override) >= 2:
            self.playlist_reload_time_override = float(self.playlist_reload_time_override)
        elif self.playlist_reload_time_override not in ["segment", "live-edge"]:
            self.playlist_reload_time_override = 0

    def _fetch_playlist(self) -> Response:
        res = self.session.http.get(
            self.stream.url,
            exception=StreamError,
            retries=self.playlist_reload_retries,
            **self.reader.request_params,
        )
        res.encoding = "utf-8"

        return res

    def reload_playlist(self):
        if self.closed:  # pragma: no cover
            return

        self.reader.buffer.wait_free()

        log.debug("Reloading playlist")
        res = self._fetch_playlist()

        try:
            playlist = parse_m3u8(res, parser=self.stream.__parser__)
        except ValueError as err:
            raise StreamError(err) from err

        if playlist.is_master:
            raise StreamError(f"Attempted to play a variant playlist, use 'hls://{self.stream.url}' instead")

        if playlist.iframes_only:
            raise StreamError("Streams containing I-frames only are not playable")

        self.playlist_targetduration = playlist.targetduration or 0
        self.playlist_reload_time = self._playlist_reload_time(playlist)

        if playlist.segments:
            self.process_segments(playlist)

    def _playlist_reload_time(self, playlist: M3U8[HLSSegment, HLSPlaylist]) -> float:
        if self.playlist_reload_time_override == "segment" and playlist.segments:
            return playlist.segments[-1].duration
        if self.playlist_reload_time_override == "live-edge" and playlist.segments:
            return sum(s.duration for s in playlist.segments[-max(1, self.live_edge - 1) :])
        if type(self.playlist_reload_time_override) is float and self.playlist_reload_time_override > 0:
            return self.playlist_reload_time_override
        if playlist.targetduration:
            return playlist.targetduration
        if playlist.segments:
            return sum(s.duration for s in playlist.segments[-max(1, self.live_edge - 1) :])

        return self.playlist_reload_time

    def process_segments(self, playlist: M3U8[HLSSegment, HLSPlaylist]) -> None:
        segments = playlist.segments
        first_segment, last_segment = segments[0], segments[-1]

        if first_segment.key and first_segment.key.method != "NONE":
            log.debug("Segments in this playlist are encrypted")

        self.playlist_changed = [s.num for s in self.playlist_segments] != [s.num for s in segments]
        self.playlist_segments = segments

        if not self.playlist_changed:
            self.playlist_reload_time = max(self.playlist_reload_time / 2, 1)

        if playlist.is_endlist:
            self.playlist_end = last_segment.num

        if self.playlist_sequence < 0:
            if self.playlist_end is None and not self.hls_live_restart:
                edge_index = -(min(len(segments), max(int(self.live_edge), 1)))
                edge_segment = segments[edge_index]
                self.playlist_sequence = edge_segment.num
            else:
                self.playlist_sequence = first_segment.num

    def valid_segment(self, segment: HLSSegment) -> bool:
        return segment.num >= self.playlist_sequence

    def _segment_queue_timing_threshold_reached(self) -> bool:
        if self.segment_queue_timing_threshold_factor <= 0:
            return False

        threshold = max(
            self.SEGMENT_QUEUE_TIMING_THRESHOLD_MIN,
            self.playlist_targetduration * self.segment_queue_timing_threshold_factor,
        )
        if now() <= self.playlist_sequence_last + timedelta(seconds=threshold):
            return False

        log.warning(f"No new segments in playlist for more than {threshold:.2f}s. Stopping...")
        return True

    @staticmethod
    def duration_to_sequence(duration: float, segments: list[HLSSegment]) -> int:
        d = 0.0
        default = -1

        segments_order = segments if duration >= 0 else reversed(segments)

        for segment in segments_order:
            if d >= abs(duration):
                return segment.num
            d += segment.duration
            default = segment.num

        # could not skip far enough, so return the default
        return default

    def iter_segments(self):
        self.playlist_reload_last \
            = self.playlist_sequence_last \
            = now()  # fmt: skip

        try:
            self.reload_playlist()
        except StreamError as err:
            log.error(f"{err}")
            self.reader.close()
            return

        if self.playlist_end is None:
            if self.duration_offset_start > 0:
                log.debug(f"Time offsets negative for live streams, skipping back {self.duration_offset_start} seconds")
            # live playlist, force offset durations back to None
            self.duration_offset_start = -self.duration_offset_start

        if self.duration_offset_start != 0:
            self.playlist_sequence = self.duration_to_sequence(self.duration_offset_start, self.playlist_segments)

        if self.playlist_segments:
            log.debug(
                "; ".join([
                    f"First Sequence: {self.playlist_segments[0].num}",
                    f"Last Sequence: {self.playlist_segments[-1].num}",
                ]),
            )
            log.debug(
                "; ".join([
                    f"Start offset: {self.duration_offset_start}",
                    f"Duration: {self.duration_limit}",
                    f"Start Sequence: {self.playlist_sequence}",
                    f"End Sequence: {self.playlist_end}",
                ]),
            )

        total_duration = 0
        while not self.closed:
            queued = False
            for segment in self.playlist_segments:
                if not self.valid_segment(segment):
                    continue

                log.debug(f"Adding segment {segment.num} to queue")
                offset = segment.num - self.playlist_sequence
                if offset > 0:
                    log.warning(
                        (
                            f"Skipped segments {self.playlist_sequence}-{segment.num - 1} after playlist reload. "
                            if offset > 1
                            else f"Skipped segment {self.playlist_sequence} after playlist reload. "
                        )
                        + "This is unsupported and will result in incoherent output data.",
                    )

                yield segment
                queued = True

                total_duration += segment.duration
                if self.duration_limit and total_duration >= self.duration_limit:
                    log.info(f"Stopping stream early after {self.duration_limit}")
                    return

                if self.closed:  # pragma: no cover
                    return

                self.playlist_sequence = segment.num + 1

            # End of stream
            if self.closed or self.playlist_end is not None and (not queued or self.playlist_sequence > self.playlist_end):
                return

            if queued:
                self.playlist_sequence_last = now()
            elif self._segment_queue_timing_threshold_reached():
                return

            # Exclude playlist fetch+processing time from the overall playlist reload time
            # and reload playlist in a strict time interval
            time_completed = now()
            time_elapsed = max(0.0, (time_completed - self.playlist_reload_last).total_seconds())
            time_wait = max(0.0, self.playlist_reload_time - time_elapsed)
            if self.wait(time_wait):
                if time_wait > 0:
                    # If we had to wait, then don't call now() twice and instead reference the timestamp from before
                    # the wait() call, to prevent a shifting time offset due to the execution time.
                    self.playlist_reload_last = time_completed + timedelta(seconds=time_wait)
                else:
                    # Otherwise, get the current time, as the reload interval already has shifted.
                    self.playlist_reload_last = now()

                try:
                    self.reload_playlist()
                except StreamError as err:
                    log.warning(f"Failed to reload playlist: {err}")


class HLSStreamReader(FilteredStream, SegmentedStreamReader[HLSSegment, Response]):
    __worker__ = HLSStreamWorker
    __writer__ = HLSStreamWriter

    worker: HLSStreamWorker
    writer: HLSStreamWriter
    stream: HLSStream
    buffer: RingBuffer

    def __init__(self, stream: HLSStream):
        self.request_params = dict(stream.args)
        # These params are reserved for internal use
        self.request_params.pop("exception", None)
        self.request_params.pop("stream", None)
        self.request_params.pop("timeout", None)
        self.request_params.pop("url", None)

        super().__init__(stream)


class MuxedHLSStream(MuxedStream["HLSStream"]):
    """
    Muxes multiple HLS video and audio streams into one output stream.
    """

    __shortname__ = "hls-multi"

    def __init__(
        self,
        session: Streamlink,
        video: str,
        audio: str | list[str],
        hlsstream: type[HLSStream] | None = None,
        url_master: str | None = None,
        multivariant: M3U8 | None = None,
        force_restart: bool = False,
        ffmpeg_options: Mapping[str, Any] | None = None,
        **kwargs,
    ):
        """
        :param session: Streamlink session instance
        :param video: Video stream URL
        :param audio: Audio stream URL or list of URLs
        :param hlsstream: The :class:`HLSStream` class of each sub-stream
        :param url_master: The URL of the HLS playlist's multivariant playlist (deprecated)
        :param multivariant: The parsed multivariant playlist
        :param force_restart: Start from the beginning after reaching the playlist's end
        :param ffmpeg_options: Additional keyword arguments passed to :class:`ffmpegmux.FFMPEGMuxer`
        :param kwargs: Additional keyword arguments passed to :class:`HLSStream`
        """

        tracks = [video]
        maps = ["0:v?", "0:a?"]
        if audio:
            if isinstance(audio, list):
                tracks.extend(audio)
            else:
                tracks.append(audio)
        maps.extend(f"{i}:a" for i in range(1, len(tracks)))

        hlsstream = hlsstream or HLSStream
        substreams = [hlsstream(session, url, force_restart=force_restart, **kwargs) for url in tracks]
        ffmpeg_options = ffmpeg_options or {}

        super().__init__(session, *substreams, format="mpegts", maps=maps, **ffmpeg_options)
        self._url_master = url_master
        self.multivariant = multivariant if multivariant and multivariant.is_master else None

    @property
    def url_master(self):
        """Deprecated"""
        return self.multivariant.uri if self.multivariant and self.multivariant.uri else self._url_master

    def to_manifest_url(self):
        url = self.multivariant.uri if self.multivariant and self.multivariant.uri else self.url_master

        if url is None:
            return super().to_manifest_url()

        return url


class HLSStream(HTTPStream):
    """
    Implementation of the Apple HTTP Live Streaming protocol.
    """

    __shortname__ = "hls"
    __reader__ = HLSStreamReader
    __parser__: ClassVar[type[M3U8Parser[M3U8[HLSSegment, HLSPlaylist], HLSSegment, HLSPlaylist]]] = M3U8Parser

    def __init__(
        self,
        session: Streamlink,
        url: str,
        url_master: str | None = None,
        multivariant: M3U8 | None = None,
        force_restart: bool = False,
        start_offset: float = 0,
        duration: float | None = None,
        **kwargs,
    ):
        """
        :param session: Streamlink session instance
        :param url: The URL of the HLS playlist
        :param url_master: The URL of the HLS playlist's multivariant playlist (deprecated)
        :param multivariant: The parsed multivariant playlist
        :param force_restart: Start from the beginning after reaching the playlist's end
        :param start_offset: Number of seconds to be skipped from the beginning
        :param duration: Number of seconds until ending the stream
        :param kwargs: Additional keyword arguments passed to :meth:`requests.Session.request`
        """

        super().__init__(session, url, **kwargs)
        self._url_master = url_master
        self.multivariant = multivariant if multivariant and multivariant.is_master else None
        self.force_restart = force_restart
        self.start_offset = start_offset
        self.duration = duration

    def __json__(self):  # noqa: PLW3201
        json = super().__json__()

        try:
            json["master"] = self.to_manifest_url()
        except TypeError:
            pass

        del json["method"]
        del json["body"]

        return json

    @property
    def url_master(self):
        """Deprecated"""
        return self.multivariant.uri if self.multivariant and self.multivariant.uri else self._url_master

    def to_manifest_url(self):
        url = self.multivariant.uri if self.multivariant and self.multivariant.uri else self.url_master

        if url is None:
            return super().to_manifest_url()

        args = self.args.copy()
        args.update(url=url)

        return self.session.http.prepare_new_request(**args).url

    def open(self):
        reader = self.__reader__(self)
        reader.open()

        return reader

    @classmethod
    def _fetch_variant_playlist(cls, session, url: str, **request_args) -> Response:
        res = session.http.get(url, exception=OSError, **request_args)
        res.encoding = "utf-8"

        return res

    @classmethod
    def parse_variant_playlist(
        cls,
        session: Streamlink,
        url: str,
        name_key: str = "name",
        name_prefix: str = "",
        check_streams: bool = False,
        force_restart: bool = False,
        name_fmt: str | None = None,
        start_offset: float = 0,
        duration: float | None = None,
        **kwargs,
    ) -> dict[str, HLSStream | MuxedHLSStream]:
        """
        Parse a variant playlist and return its streams.

        :param session: Streamlink session instance
        :param url: The URL of the variant playlist
        :param name_key: Prefer to use this key as stream name, valid keys are: name, pixels, bitrate
        :param name_prefix: Add this prefix to the stream names
        :param check_streams: Only allow streams that are accessible
        :param force_restart: Start at the first segment even for a live stream
        :param name_fmt: A format string for the name, allowed format keys are: name, pixels, bitrate
        :param start_offset: Number of seconds to be skipped from the beginning
        :param duration: Number of second until ending the stream
        :param kwargs: Additional keyword arguments passed to :class:`HLSStream`, :class:`MuxedHLSStream`,
                       or :py:meth:`requests.Session.request`
        """

        locale = session.localization
        hls_audio_select = session.options.get("hls-audio-select")
        audio_select_any: bool = "*" in hls_audio_select
        audio_select_langs: list[Language] = []
        audio_select_codes: list[str] = []

        for item in hls_audio_select:
            item = item.strip().lower()
            if item == "*":
                continue
            try:
                audio_select_langs.append(Language.get(item))
            except LookupError:
                audio_select_codes.append(item)

        request_args = session.http.valid_request_args(**kwargs)
        res = cls._fetch_variant_playlist(session, url, **request_args)

        try:
            multivariant = parse_m3u8(res, parser=cls.__parser__)
        except ValueError as err:
            raise OSError(f"Failed to parse playlist: {err}") from err

        stream_name: str | None
        stream: HLSStream | MuxedHLSStream
        streams: dict[str, HLSStream | MuxedHLSStream] = {}

        for playlist in multivariant.playlists:
            if playlist.is_iframe:
                continue

            names: dict[str, str | None] = dict(name=None, pixels=None, bitrate=None)
            audio_streams = []
            fallback_audio: list[Media] = []
            default_audio: list[Media] = []
            preferred_audio: list[Media] = []

            for media in playlist.media:
                if media.type == "VIDEO" and media.name:
                    names["name"] = media.name
                elif media.type == "AUDIO":
                    audio_streams.append(media)

            for media in audio_streams:
                # Media without a URI is not relevant as external audio
                if not media.uri:
                    continue

                if not fallback_audio and media.default:
                    fallback_audio = [media]

                # if the media is "autoselect" and it better matches the users preferences, use that
                # instead of default
                if not default_audio and (media.autoselect and locale.equivalent(language=media.parsed_language)):
                    default_audio = [media]

                # select the first audio stream that matches the user's explict language selection
                if (
                    # user has selected all languages
                    audio_select_any
                    # compare plain language codes first
                    or (
                        media.language is not None
                        and media.language in audio_select_codes
                    )
                    # then compare parsed language codes and user input
                    or (
                        media.parsed_language is not None
                        and media.parsed_language in audio_select_langs
                    )
                    # then compare media name attribute
                    or (
                        media.name
                        and media.name.lower() in audio_select_codes
                    )
                    # fallback: find first media playlist matching the user's locale
                    or (
                        (not preferred_audio or media.default)
                        and locale.explicit
                        and locale.equivalent(language=media.parsed_language)
                    )
                ):  # fmt: skip
                    preferred_audio.append(media)

            # final fallback on the first audio stream listed
            if not fallback_audio and audio_streams and audio_streams[0].uri:
                fallback_audio = [audio_streams[0]]

            if playlist.stream_info.resolution and playlist.stream_info.resolution.height:
                names["pixels"] = f"{playlist.stream_info.resolution.height}p"

            if playlist.stream_info.bandwidth:
                bw = playlist.stream_info.bandwidth

                if bw >= 1000:
                    names["bitrate"] = f"{int(bw / 1000.0)}k"
                else:
                    names["bitrate"] = f"{bw / 1000.0}k"

            if name_fmt:
                stream_name = name_fmt.format(**names)
            else:
                stream_name = (
                    names.get(name_key)
                    or names.get("name")
                    or names.get("pixels")
                    or names.get("bitrate")
                )  # fmt: skip

            if not stream_name:
                continue
            if name_prefix:
                stream_name = f"{name_prefix}{stream_name}"

            if stream_name in streams:  # rename duplicate streams
                stream_name = f"{stream_name}_alt"
                num_alts = len([k for k in streams.keys() if k.startswith(stream_name)])

                # We shouldn't need more than 2 alt streams
                if num_alts >= 2:
                    continue
                elif num_alts > 0:
                    stream_name = f"{stream_name}{num_alts + 1}"

            if check_streams:
                # noinspection PyBroadException
                try:
                    session.http.get(playlist.uri, **request_args)
                except KeyboardInterrupt:
                    raise
                except Exception:
                    continue

            external_audio = preferred_audio or default_audio or fallback_audio

            if external_audio and FFMPEGMuxer.is_usable(session):
                external_audio_msg = ", ".join([
                    f"(language={x.language}, name={x.name or 'N/A'})"
                    for x in external_audio
                ])  # fmt: skip
                log.debug(f"Using external audio tracks for stream {stream_name} {external_audio_msg}")

                stream = MuxedHLSStream(
                    session,
                    video=playlist.uri,
                    audio=[x.uri for x in external_audio if x.uri],
                    hlsstream=cls,
                    multivariant=multivariant,
                    force_restart=force_restart,
                    start_offset=start_offset,
                    duration=duration,
                    **kwargs,
                )
            else:
                stream = cls(
                    session,
                    playlist.uri,
                    multivariant=multivariant,
                    force_restart=force_restart,
                    start_offset=start_offset,
                    duration=duration,
                    **kwargs,
                )

            streams[stream_name] = stream

        return streams
