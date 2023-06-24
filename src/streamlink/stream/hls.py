import logging
import re
import struct
from concurrent.futures import Future
from datetime import datetime, timedelta
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union
from urllib.parse import urlparse

# noinspection PyPackageRequirements
from Crypto.Cipher import AES

# noinspection PyPackageRequirements
from Crypto.Util.Padding import unpad
from requests import Response
from requests.exceptions import ChunkedEncodingError, ConnectionError, ContentDecodingError, InvalidSchema

from streamlink.buffers import RingBuffer
from streamlink.exceptions import StreamError
from streamlink.session import Streamlink
from streamlink.stream.ffmpegmux import FFMPEGMuxer, MuxedStream
from streamlink.stream.filtered import FilteredStream
from streamlink.stream.hls_playlist import M3U8, ByteRange, Key, Map, Media, Segment, load as load_hls_playlist
from streamlink.stream.http import HTTPStream
from streamlink.stream.segmented import SegmentedStreamReader, SegmentedStreamWorker, SegmentedStreamWriter
from streamlink.utils.cache import LRUCache
from streamlink.utils.formatter import Formatter
from streamlink.utils.times import now


log = logging.getLogger(__name__)


class Sequence(NamedTuple):
    num: int
    segment: Segment


class ByteRangeOffset:
    sequence: Optional[int] = None
    offset: Optional[int] = None

    @staticmethod
    def _calc_end(start: int, size: int) -> int:
        return start + max(size - 1, 0)

    def cached(self, sequence: int, byterange: ByteRange) -> Tuple[int, int]:
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

    def uncached(self, byterange: ByteRange) -> Tuple[int, int]:
        bytes_start = byterange.offset
        if bytes_start is None:
            raise StreamError("Missing BYTERANGE offset")

        return bytes_start, self._calc_end(bytes_start, byterange.range)


class HLSStreamWriter(SegmentedStreamWriter):
    WRITE_CHUNK_SIZE = 8192

    reader: "HLSStreamReader"
    stream: "HLSStream"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        options = self.session.options

        self.byterange: ByteRangeOffset = ByteRangeOffset()
        self.map_cache: LRUCache[str, Future] = LRUCache(self.threads)
        self.key_data: Union[bytes, bytearray, memoryview] = b""
        self.key_uri: Optional[str] = None
        self.key_uri_override = options.get("hls-segment-key-uri")
        self.stream_data = options.get("hls-segment-stream-data")

        self.ignore_names: Optional[re.Pattern] = None
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

    def create_request_params(self, num: int, segment: Union[Segment, Map], is_map: bool):
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

    def put(self, sequence: Sequence):
        if self.closed:
            return

        if sequence is None:
            self.queue(None, None)
            return

        # always queue the segment's map first if it exists
        if sequence.segment.map is not None:
            cached_map_future = self.map_cache.get(sequence.segment.map.uri)
            # use cached map request if not a stream discontinuity
            # don't fetch multiple times when map request of previous segment is still pending
            if cached_map_future is not None and not sequence.segment.discontinuity:
                future = cached_map_future
            else:
                future = self.executor.submit(self.fetch_map, sequence)
                self.map_cache.set(sequence.segment.map.uri, future)
            self.queue(sequence, future, True)

        # regular segment request
        future = self.executor.submit(self.fetch, sequence)
        self.queue(sequence, future, False)

    def fetch(self, sequence: Sequence) -> Optional[Response]:
        try:
            return self._fetch(
                sequence.segment.uri,
                stream=self.stream_data,
                **self.create_request_params(sequence.num, sequence.segment, False),
            )
        except StreamError as err:
            log.error(f"Failed to fetch segment {sequence.num}: {err}")

    def fetch_map(self, sequence: Sequence) -> Optional[Response]:
        _map: Map = sequence.segment.map  # type: ignore[assignment]  # map is not None
        try:
            return self._fetch(
                _map.uri,
                stream=False,
                **self.create_request_params(sequence.num, _map, True),
            )
        except StreamError as err:
            log.error(f"Failed to fetch map for segment {sequence.num}: {err}")

    def _fetch(self, url: str, **request_params) -> Optional[Response]:
        if self.closed or not self.retries:  # pragma: no cover
            return None

        return self.session.http.get(
            url,
            timeout=self.timeout,
            retries=self.retries,
            exception=StreamError,
            **request_params,
        )

    def should_filter_sequence(self, sequence: Sequence) -> bool:
        return self.ignore_names is not None and self.ignore_names.search(sequence.segment.uri) is not None

    def write(self, sequence: Sequence, result: Response, *data):
        if not self.should_filter_sequence(sequence):
            log.debug(f"Writing segment {sequence.num} to output")

            written_once = self.reader.buffer.written_once
            try:
                return self._write(sequence, result, *data)
            finally:
                is_paused = self.reader.is_paused()

                # Depending on the filtering implementation, the segment's discontinuity attribute can be missing.
                # Also check if the output will be resumed after data has already been written to the buffer before.
                if sequence.segment.discontinuity or is_paused and written_once:
                    log.warning(
                        "Encountered a stream discontinuity. This is unsupported and will result in incoherent output data.",
                    )

                # unblock reader thread after writing data to the buffer
                if is_paused:
                    log.info("Resuming stream output")
                    self.reader.resume()

        else:
            log.debug(f"Discarding segment {sequence.num}")

            # Read and discard any remaining HTTP response data in the response connection.
            # Unread data in the HTTPResponse connection blocks the connection from being released back to the pool.
            result.raw.drain_conn()

            # block reader thread if filtering out segments
            if not self.reader.is_paused():
                log.info("Filtering out segments and pausing stream output")
                self.reader.pause()

    def _write(self, sequence: Sequence, result: Response, is_map: bool):
        if sequence.segment.key and sequence.segment.key.method != "NONE":
            try:
                decryptor = self.create_decryptor(sequence.segment.key, sequence.num)
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
                log.error(f"Download of segment {sequence.num} failed: {err}")
                return
            except ValueError as err:
                log.error(f"Error while decrypting segment {sequence.num}: {err}")
                return

        else:
            try:
                for chunk in result.iter_content(self.WRITE_CHUNK_SIZE):
                    self.reader.buffer.write(chunk)
            except (ChunkedEncodingError, ContentDecodingError, ConnectionError) as err:
                log.error(f"Download of segment {sequence.num} failed: {err}")
                return

        if is_map:
            log.debug(f"Segment initialization {sequence.num} complete")
        else:
            log.debug(f"Segment {sequence.num} complete")


class HLSStreamWorker(SegmentedStreamWorker):
    reader: "HLSStreamReader"
    writer: "HLSStreamWriter"
    stream: "HLSStream"

    SEGMENT_QUEUE_TIMING_THRESHOLD_FACTOR = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.playlist_changed = False
        self.playlist_end: Optional[int] = None
        self.playlist_targetduration: float = 0
        self.playlist_sequence: int = -1
        self.playlist_sequences: List[Sequence] = []
        self.playlist_sequences_last: datetime = now()
        self.playlist_reload_last: datetime = now()
        self.playlist_reload_time: float = 6
        self.playlist_reload_time_override = self.session.options.get("hls-playlist-reload-time")
        self.playlist_reload_retries = self.session.options.get("hls-playlist-reload-attempts")
        self.live_edge = self.session.options.get("hls-live-edge")
        self.duration_offset_start = int(self.stream.start_offset + (self.session.options.get("hls-start-offset") or 0))
        self.duration_limit = self.stream.duration or (
            int(self.session.options.get("hls-duration")) if self.session.options.get("hls-duration") else None)
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

    # TODO: rename to _parse_playlist
    def _reload_playlist(self, *args, **kwargs):
        return load_hls_playlist(*args, **kwargs)

    def reload_playlist(self):
        if self.closed:  # pragma: no cover
            return

        self.reader.buffer.wait_free()

        log.debug("Reloading playlist")
        res = self._fetch_playlist()

        try:
            playlist = self._reload_playlist(res)
        except ValueError as err:
            raise StreamError(err) from err

        if playlist.is_master:
            raise StreamError(f"Attempted to play a variant playlist, use 'hls://{self.stream.url}' instead")

        if playlist.iframes_only:
            raise StreamError("Streams containing I-frames only are not playable")

        media_sequence = playlist.media_sequence or 0
        sequences = [Sequence(media_sequence + i, s)
                     for i, s in enumerate(playlist.segments)]

        self.playlist_targetduration = playlist.targetduration or 0
        self.playlist_reload_time = self._playlist_reload_time(playlist, sequences)

        if sequences:
            self.process_sequences(playlist, sequences)

    def _playlist_reload_time(self, playlist: M3U8, sequences: List[Sequence]) -> float:
        if self.playlist_reload_time_override == "segment" and sequences:
            return sequences[-1].segment.duration
        if self.playlist_reload_time_override == "live-edge" and sequences:
            return sum(s.segment.duration for s in sequences[-max(1, self.live_edge - 1):])
        if type(self.playlist_reload_time_override) is float and self.playlist_reload_time_override > 0:
            return self.playlist_reload_time_override
        if playlist.targetduration:
            return playlist.targetduration
        if sequences:
            return sum(s.segment.duration for s in sequences[-max(1, self.live_edge - 1):])

        return self.playlist_reload_time

    def process_sequences(self, playlist: M3U8, sequences: List[Sequence]) -> None:
        first_sequence, last_sequence = sequences[0], sequences[-1]

        if first_sequence.segment.key and first_sequence.segment.key.method != "NONE":
            log.debug("Segments in this playlist are encrypted")

        self.playlist_changed = ([s.num for s in self.playlist_sequences] != [s.num for s in sequences])
        self.playlist_sequences = sequences

        if not self.playlist_changed:
            self.playlist_reload_time = max(self.playlist_reload_time / 2, 1)

        if playlist.is_endlist:
            self.playlist_end = last_sequence.num

        if self.playlist_sequence < 0:
            if self.playlist_end is None and not self.hls_live_restart:
                edge_index = -(min(len(sequences), max(int(self.live_edge), 1)))
                edge_sequence = sequences[edge_index]
                self.playlist_sequence = edge_sequence.num
            else:
                self.playlist_sequence = first_sequence.num

    def valid_sequence(self, sequence: Sequence) -> bool:
        return sequence.num >= self.playlist_sequence

    def _segment_queue_timing_threshold_reached(self) -> bool:
        threshold = self.playlist_targetduration * self.SEGMENT_QUEUE_TIMING_THRESHOLD_FACTOR
        if now() <= self.playlist_sequences_last + timedelta(seconds=threshold):
            return False

        log.warning(f"No new segments in playlist for more than {threshold:.2f}s. Stopping...")
        return True

    @staticmethod
    def duration_to_sequence(duration: float, sequences: List[Sequence]) -> int:
        d = 0.0
        default = -1

        sequences_order = sequences if duration >= 0 else reversed(sequences)

        for sequence in sequences_order:
            if d >= abs(duration):
                return sequence.num
            d += sequence.segment.duration
            default = sequence.num

        # could not skip far enough, so return the default
        return default

    def iter_segments(self):
        self.playlist_reload_last \
            = self.playlist_sequences_last \
            = now()

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
            self.playlist_sequence = self.duration_to_sequence(self.duration_offset_start, self.playlist_sequences)

        if self.playlist_sequences:
            log.debug("; ".join([
                f"First Sequence: {self.playlist_sequences[0].num}",
                f"Last Sequence: {self.playlist_sequences[-1].num}",
            ]))
            log.debug("; ".join([
                f"Start offset: {self.duration_offset_start}",
                f"Duration: {self.duration_limit}",
                f"Start Sequence: {self.playlist_sequence}",
                f"End Sequence: {self.playlist_end}",
            ]))

        total_duration = 0
        while not self.closed:
            queued = False
            for sequence in filter(self.valid_sequence, self.playlist_sequences):
                log.debug(f"Adding segment {sequence.num} to queue")
                yield sequence
                queued = True

                total_duration += sequence.segment.duration
                if self.duration_limit and total_duration >= self.duration_limit:
                    log.info(f"Stopping stream early after {self.duration_limit}")
                    return

                # End of stream
                stream_end = self.playlist_end is not None and sequence.num >= self.playlist_end
                if self.closed or stream_end:
                    return

                self.playlist_sequence = sequence.num + 1

            if queued:
                self.playlist_sequences_last = now()
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


class HLSStreamReader(FilteredStream, SegmentedStreamReader):
    __worker__ = HLSStreamWorker
    __writer__ = HLSStreamWriter

    worker: "HLSStreamWorker"
    writer: "HLSStreamWriter"
    stream: "HLSStream"
    buffer: RingBuffer

    def __init__(self, stream: "HLSStream"):
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
        audio: Union[str, List[str]],
        url_master: Optional[str] = None,
        multivariant: Optional[M3U8] = None,
        force_restart: bool = False,
        ffmpeg_options: Optional[Dict[str, Any]] = None,
        **args,
    ):
        """
        :param session: Streamlink session instance
        :param video: Video stream URL
        :param audio: Audio stream URL or list of URLs
        :param url_master: The URL of the HLS playlist's multivariant playlist (deprecated)
        :param multivariant: The parsed multivariant playlist
        :param force_restart: Start from the beginning after reaching the playlist's end
        :param ffmpeg_options: Additional keyword arguments passed to :class:`ffmpegmux.FFMPEGMuxer`
        :param args: Additional keyword arguments passed to :class:`HLSStream`
        """

        tracks = [video]
        maps = ["0:v?", "0:a?"]
        if audio:
            if isinstance(audio, list):
                tracks.extend(audio)
            else:
                tracks.append(audio)
        maps.extend(f"{i}:a" for i in range(1, len(tracks)))
        substreams = [HLSStream(session, url, force_restart=force_restart, **args) for url in tracks]
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

    def __init__(
        self,
        session_,
        url: str,
        url_master: Optional[str] = None,
        multivariant: Optional[M3U8] = None,
        force_restart: bool = False,
        start_offset: float = 0,
        duration: Optional[float] = None,
        **args,
    ):
        """
        :param streamlink.session.Streamlink session_: Streamlink session instance
        :param url: The URL of the HLS playlist
        :param url_master: The URL of the HLS playlist's multivariant playlist (deprecated)
        :param multivariant: The parsed multivariant playlist
        :param force_restart: Start from the beginning after reaching the playlist's end
        :param start_offset: Number of seconds to be skipped from the beginning
        :param duration: Number of seconds until ending the stream
        :param args: Additional keyword arguments passed to :meth:`requests.Session.request`
        """

        super().__init__(session_, url, **args)
        self._url_master = url_master
        self.multivariant = multivariant if multivariant and multivariant.is_master else None
        self.force_restart = force_restart
        self.start_offset = start_offset
        self.duration = duration

    def __json__(self):
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
    def _fetch_variant_playlist(cls, session, url: str, **request_params) -> Response:
        res = session.http.get(url, exception=OSError, **request_params)
        res.encoding = "utf-8"

        return res

    # TODO: rename to _parse_variant_playlist
    @classmethod
    def _get_variant_playlist(cls, *args, **kwargs):
        return load_hls_playlist(*args, **kwargs)

    @classmethod
    def parse_variant_playlist(
        cls,
        session_,
        url: str,
        name_key: str = "name",
        name_prefix: str = "",
        check_streams: bool = False,
        force_restart: bool = False,
        name_fmt: Optional[str] = None,
        start_offset: float = 0,
        duration: Optional[float] = None,
        **request_params,
    ) -> Dict[str, Union["HLSStream", "MuxedHLSStream"]]:
        """
        Parse a variant playlist and return its streams.

        :param streamlink.session.Streamlink session_: Streamlink session instance
        :param url: The URL of the variant playlist
        :param name_key: Prefer to use this key as stream name, valid keys are: name, pixels, bitrate
        :param name_prefix: Add this prefix to the stream names
        :param check_streams: Only allow streams that are accessible
        :param force_restart: Start at the first segment even for a live stream
        :param name_fmt: A format string for the name, allowed format keys are: name, pixels, bitrate
        :param start_offset: Number of seconds to be skipped from the beginning
        :param duration: Number of second until ending the stream
        :param request_params: Additional keyword arguments passed to :class:`HLSStream`, :class:`MuxedHLSStream`,
                               or :py:meth:`requests.Session.request`
        """

        locale = session_.localization
        audio_select = session_.options.get("hls-audio-select")

        res = cls._fetch_variant_playlist(session_, url, **request_params)

        try:
            multivariant = cls._get_variant_playlist(res)
        except ValueError as err:
            raise OSError(f"Failed to parse playlist: {err}") from err

        stream_name: Optional[str]
        stream: Union["HLSStream", "MuxedHLSStream"]
        streams: Dict[str, Union["HLSStream", "MuxedHLSStream"]] = {}

        for playlist in filter(lambda p: not p.is_iframe, multivariant.playlists):
            names: Dict[str, Optional[str]] = dict(name=None, pixels=None, bitrate=None)
            audio_streams = []
            fallback_audio: List[Media] = []
            default_audio: List[Media] = []
            preferred_audio: List[Media] = []

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
                if not default_audio and (media.autoselect and locale.equivalent(language=media.language)):
                    default_audio = [media]

                # select the first audio stream that matches the user's explict language selection
                if (
                    (
                        "*" in audio_select
                        or media.language in audio_select
                        or media.name in audio_select
                    )
                    or (
                        (not preferred_audio or media.default)
                        and locale.explicit
                        and locale.equivalent(language=media.language)
                    )
                ):
                    preferred_audio.append(media)

            # final fallback on the first audio stream listed
            if not fallback_audio and len(audio_streams) and audio_streams[0].uri:
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
                )

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
                    session_.http.get(playlist.uri, **request_params)
                except KeyboardInterrupt:
                    raise
                except Exception:
                    continue

            external_audio = preferred_audio or default_audio or fallback_audio

            if external_audio and FFMPEGMuxer.is_usable(session_):
                external_audio_msg = ", ".join([
                    f"(language={x.language}, name={x.name or 'N/A'})"
                    for x in external_audio
                ])
                log.debug(f"Using external audio tracks for stream {stream_name} {external_audio_msg}")

                stream = MuxedHLSStream(
                    session_,
                    video=playlist.uri,
                    audio=[x.uri for x in external_audio if x.uri],
                    multivariant=multivariant,
                    force_restart=force_restart,
                    start_offset=start_offset,
                    duration=duration,
                    **request_params,
                )
            else:
                stream = cls(
                    session_,
                    playlist.uri,
                    multivariant=multivariant,
                    force_restart=force_restart,
                    start_offset=start_offset,
                    duration=duration,
                    **request_params,
                )

            streams[stream_name] = stream

        return streams
