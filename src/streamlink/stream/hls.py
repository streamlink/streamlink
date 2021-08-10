import logging
import re
import struct
from collections import OrderedDict, defaultdict
from concurrent.futures import Future
from threading import Event
from typing import List, NamedTuple, Optional, Union
from urllib.parse import urlparse

# noinspection PyPackageRequirements
from Crypto.Cipher import AES
# noinspection PyPackageRequirements
from Crypto.Util.Padding import unpad
from requests import Response
from requests.exceptions import ChunkedEncodingError, ConnectionError, ContentDecodingError

from streamlink.exceptions import StreamError
from streamlink.stream import hls_playlist
from streamlink.stream.ffmpegmux import FFMPEGMuxer, MuxedStream
from streamlink.stream.hls_playlist import Key, M3U8, Map, Segment
from streamlink.stream.http import HTTPStream
from streamlink.stream.segmented import (SegmentedStreamReader, SegmentedStreamWorker, SegmentedStreamWriter)
from streamlink.utils import LRUCache, LazyFormatter

log = logging.getLogger(__name__)


class Sequence(NamedTuple):
    num: int
    segment: Segment


class HLSStreamWriter(SegmentedStreamWriter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        options = self.session.options

        self.byterange_offsets = defaultdict(int)
        self.map_cache: LRUCache[Sequence.segment.map.uri, Future] = LRUCache(self.threads)
        self.key_data = None
        self.key_uri = None
        self.key_uri_override = options.get("hls-segment-key-uri")

        self.ignore_names = False
        ignore_names = {*options.get("hls-segment-ignore-names")}
        if ignore_names:
            segments = "|".join(map(re.escape, ignore_names))
            self.ignore_names = re.compile(rf"(?:{segments})\.ts", re.IGNORECASE)

    @staticmethod
    def num_to_iv(n: int) -> bytes:
        return struct.pack(">8xq", n)

    def create_decryptor(self, key: Key, num: int) -> AES:
        if key.method != "AES-128":
            raise StreamError("Unable to decrypt cipher {0}", key.method)

        if not self.key_uri_override and not key.uri:
            raise StreamError("Missing URI to decryption key")

        if self.key_uri_override:
            p = urlparse(key.uri)
            key_uri = LazyFormatter.format(
                self.key_uri_override,
                url=key.uri,
                scheme=p.scheme,
                netloc=p.netloc,
                path=p.path,
                query=p.query,
            )
        else:
            key_uri = key.uri

        if self.key_uri != key_uri:
            res = self.session.http.get(key_uri, exception=StreamError,
                                        retries=self.retries,
                                        **self.reader.request_params)
            res.encoding = "binary/octet-stream"
            self.key_data = res.content
            self.key_uri = key_uri

        iv = key.iv or self.num_to_iv(num)

        # Pad IV if needed
        iv = b"\x00" * (16 - len(iv)) + iv

        return AES.new(self.key_data, AES.MODE_CBC, iv)

    def create_request_params(self, segment: Union[Segment, Map]):
        request_params = dict(self.reader.request_params)
        headers = request_params.pop("headers", {})

        if segment.byterange:
            bytes_start = self.byterange_offsets[segment.uri]
            if segment.byterange.offset is not None:
                bytes_start = segment.byterange.offset

            bytes_len = max(segment.byterange.range - 1, 0)
            bytes_end = bytes_start + bytes_len
            headers["Range"] = f"bytes={bytes_start}-{bytes_end}"
            self.byterange_offsets[segment.uri] = bytes_end + 1

        request_params["headers"] = headers

        return request_params

    def put(self, sequence: Sequence):
        if self.closed:
            return

        if sequence is None:
            self.queue(None, None)
        else:
            # always queue the segment's map first if it exists
            if sequence.segment.map is not None:
                future = self.map_cache.get(sequence.segment.map.uri)
                # use cached map request if not a stream discontinuity
                # don't fetch multiple times when map request of previous segment is still pending
                if future is None or sequence.segment.discontinuity:
                    future = self.executor.submit(self.fetch_map, sequence)
                    self.map_cache.set(sequence.segment.map.uri, future)
                self.queue(sequence, future, True)

            # regular segment request
            future = self.executor.submit(self.fetch, sequence)
            self.queue(sequence, future, False)

    def fetch(self, sequence: Sequence) -> Optional[Response]:
        try:
            return self._fetch(sequence.segment, not sequence.segment.key)
        except StreamError as err:  # pragma: no cover
            log.error(f"Failed to fetch segment {sequence.num}: {err}")

    def fetch_map(self, sequence: Sequence) -> Optional[Response]:
        try:
            return self._fetch(sequence.segment.map, False)
        except StreamError as err:  # pragma: no cover
            log.error(f"Failed to fetch map for segment {sequence.num}: {err}")

    def _fetch(self, segment: Union[Segment, Map], stream: bool) -> Optional[Response]:
        if self.closed or not self.retries:  # pragma: no cover
            return

        request_params = self.create_request_params(segment)

        return self.session.http.get(
            segment.uri,
            stream=stream,
            timeout=self.timeout,
            exception=StreamError,
            retries=self.retries,
            **request_params
        )

    def should_filter_sequence(self, sequence: Sequence) -> bool:
        return self.ignore_names and self.ignore_names.search(sequence.segment.uri) is not None

    def write(self, sequence: Sequence, *args, **kwargs):
        if not self.should_filter_sequence(sequence):
            try:
                return self._write(sequence, *args, **kwargs)
            finally:
                # unblock reader thread after writing data to the buffer
                if not self.reader.filter_event.is_set():
                    log.info("Resuming stream output")
                    self.reader.filter_event.set()

        # block reader thread if filtering out segments
        elif self.reader.filter_event.is_set():
            log.info("Filtering out segments and pausing stream output")
            self.reader.filter_event.clear()

    def _write(self, sequence: Sequence, res: Response, is_map: bool):
        if sequence.segment.key and sequence.segment.key.method != "NONE":
            try:
                decryptor = self.create_decryptor(sequence.segment.key, sequence.num)
            except StreamError as err:
                log.error(f"Failed to create decryptor: {err}")
                self.close()
                return

            data = res.content
            # If the input data is not a multiple of 16, cut off any garbage
            garbage_len = len(data) % AES.block_size
            if garbage_len:
                log.debug(f"Cutting off {garbage_len} bytes of garbage before decrypting")
                decrypted_chunk = decryptor.decrypt(data[:-garbage_len])
            else:
                decrypted_chunk = decryptor.decrypt(data)

            chunk = unpad(decrypted_chunk, AES.block_size, style="pkcs7")
            self.reader.buffer.write(chunk)
        else:
            try:
                for chunk in res.iter_content(8192):
                    self.reader.buffer.write(chunk)
            except (ChunkedEncodingError, ContentDecodingError, ConnectionError) as err:
                log.error(f"Download of segment {sequence.num} failed ({err})")
                return

        if is_map:
            log.debug(f"Segment initialization {sequence.num} complete")
        else:
            log.debug(f"Segment {sequence.num} complete")


class HLSStreamWorker(SegmentedStreamWorker):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stream = self.reader.stream

        self.playlist_changed = False
        self.playlist_end: Optional[Sequence.num] = None
        self.playlist_sequence: int = -1
        self.playlist_sequences: List[Sequence] = []
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

    def _reload_playlist(self, text, url):
        return hls_playlist.load(text, url)

    def reload_playlist(self):
        if self.closed:  # pragma: no cover
            return

        self.reader.buffer.wait_free()
        log.debug("Reloading playlist")
        res = self.session.http.get(self.stream.url,
                                    exception=StreamError,
                                    retries=self.playlist_reload_retries,
                                    **self.reader.request_params)
        try:
            playlist = self._reload_playlist(res.text, res.url)
        except ValueError as err:
            raise StreamError(err)

        if playlist.is_master:
            raise StreamError(f"Attempted to play a variant playlist, use 'hls://{self.stream.url}' instead")

        if playlist.iframes_only:
            raise StreamError("Streams containing I-frames only are not playable")

        media_sequence = playlist.media_sequence or 0
        sequences = [Sequence(media_sequence + i, s)
                     for i, s in enumerate(playlist.segments)]

        self.playlist_reload_time = self._playlist_reload_time(playlist, sequences)

        if sequences:
            self.process_sequences(playlist, sequences)

    def _playlist_reload_time(self, playlist: M3U8, sequences: List[Sequence]) -> float:
        if self.playlist_reload_time_override == "segment" and sequences:
            return sequences[-1].segment.duration
        if self.playlist_reload_time_override == "live-edge" and sequences:
            return sum([s.segment.duration for s in sequences[-max(1, self.live_edge - 1):]])
        if type(self.playlist_reload_time_override) is float and self.playlist_reload_time_override > 0:
            return self.playlist_reload_time_override
        if playlist.target_duration:
            return playlist.target_duration
        if sequences:
            return sum([s.segment.duration for s in sequences[-max(1, self.live_edge - 1):]])

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

    @staticmethod
    def duration_to_sequence(duration: int, sequences: List[Sequence]) -> int:
        d = 0
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
        try:
            self.reload_playlist()
        except StreamError as err:
            log.error(f'{err}')
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
            log.debug(f"First Sequence: {self.playlist_sequences[0].num}; "
                      f"Last Sequence: {self.playlist_sequences[-1].num}")
            log.debug(f"Start offset: {self.duration_offset_start}; "
                      f"Duration: {self.duration_limit}; "
                      f"Start Sequence: {self.playlist_sequence}; "
                      f"End Sequence: {self.playlist_end}")

        total_duration = 0
        while not self.closed:
            for sequence in filter(self.valid_sequence, self.playlist_sequences):
                log.debug(f"Adding segment {sequence.num} to queue")
                yield sequence
                total_duration += sequence.segment.duration
                if self.duration_limit and total_duration >= self.duration_limit:
                    log.info(f"Stopping stream early after {self.duration_limit}")
                    return

                # End of stream
                stream_end = self.playlist_end and sequence.num >= self.playlist_end
                if self.closed or stream_end:
                    return

                self.playlist_sequence = sequence.num + 1

            if self.wait(self.playlist_reload_time):
                try:
                    self.reload_playlist()
                except StreamError as err:
                    log.warning(f"Failed to reload playlist: {err}")


class HLSStreamReader(SegmentedStreamReader):
    __worker__ = HLSStreamWorker
    __writer__ = HLSStreamWriter

    def __init__(self, stream):
        self.request_params = dict(stream.args)
        # These params are reserved for internal use
        self.request_params.pop("exception", None)
        self.request_params.pop("stream", None)
        self.request_params.pop("timeout", None)
        self.request_params.pop("url", None)

        self.filter_event = Event()
        self.filter_event.set()

        super().__init__(stream)

    def read(self, size):
        while True:
            try:
                return super().read(size)
            except OSError:
                # wait indefinitely until filtering ends
                self.filter_event.wait()
                if self.buffer.closed:
                    return b""
                # if data is available, try reading again
                if self.buffer.length > 0:
                    continue
                # raise if not filtering and no data available
                raise

    def close(self):
        super().close()
        self.filter_event.set()


class MuxedHLSStream(MuxedStream):
    __shortname__ = "hls-multi"

    def __init__(self, session, video, audio, url_master=None, force_restart=False, ffmpeg_options=None, **args):
        tracks = [video]
        maps = ["0:v?", "0:a?"]
        if audio:
            if isinstance(audio, list):
                tracks.extend(audio)
            else:
                tracks.append(audio)
        for i in range(1, len(tracks)):
            maps.append("{0}:a".format(i))
        substreams = map(lambda url: HLSStream(session, url, force_restart=force_restart, **args), tracks)
        ffmpeg_options = ffmpeg_options or {}

        super().__init__(session, *substreams, format="mpegts", maps=maps, **ffmpeg_options)
        self.url_master = url_master

    def to_manifest_url(self):
        return self.url_master


class HLSStream(HTTPStream):
    """Implementation of the Apple HTTP Live Streaming protocol

    *Attributes:*

    - :attr:`url` The URL to the HLS playlist.
    - :attr:`args` A :class:`dict` containing keyword arguments passed
      to :meth:`requests.request`, such as headers and cookies.

    """

    __shortname__ = "hls"
    __reader__ = HLSStreamReader

    def __init__(self, session_, url, url_master=None, force_restart=False, start_offset=0, duration=None, **args):
        super().__init__(session_, url, **args)
        self.url_master = url_master
        self.force_restart = force_restart
        self.start_offset = start_offset
        self.duration = duration

    def __repr__(self):
        return f"<HLSStream({self.url!r}, {self.url_master!r})>"

    def __json__(self):
        json = super().__json__()

        if self.url_master:
            json["master"] = self.url_master

        # Pretty sure HLS is GET only.
        del json["method"]
        del json["body"]

        return json

    def to_manifest_url(self):
        return self.url_master

    def open(self):
        reader = self.__reader__(self)
        reader.open()

        return reader

    @classmethod
    def _get_variant_playlist(cls, res):
        return hls_playlist.load(res.text, base_uri=res.url)

    @classmethod
    def parse_variant_playlist(cls, session_, url, name_key="name",
                               name_prefix="", check_streams=False,
                               force_restart=False, name_fmt=None,
                               start_offset=0, duration=None,
                               **request_params):
        """Attempts to parse a variant playlist and return its streams.

        :param url: The URL of the variant playlist.
        :param name_key: Prefer to use this key as stream name, valid keys are:
                         name, pixels, bitrate.
        :param name_prefix: Add this prefix to the stream names.
        :param check_streams: Only allow streams that are accessible.
        :param force_restart: Start at the first segment even for a live stream
        :param name_fmt: A format string for the name, allowed format keys are
                         name, pixels, bitrate.
        """
        locale = session_.localization
        audio_select = session_.options.get("hls-audio-select") or []

        res = session_.http.get(url, exception=IOError, **request_params)

        try:
            parser = cls._get_variant_playlist(res)
        except ValueError as err:
            raise OSError("Failed to parse playlist: {0}".format(err))

        streams = OrderedDict()
        for playlist in filter(lambda p: not p.is_iframe, parser.playlists):
            names = dict(name=None, pixels=None, bitrate=None)
            audio_streams = []
            fallback_audio = []
            default_audio = []
            preferred_audio = []
            for media in playlist.media:
                if media.type == "VIDEO" and media.name:
                    names["name"] = media.name
                elif media.type == "AUDIO":
                    audio_streams.append(media)
            for media in audio_streams:
                # Media without a uri is not relevant as external audio
                if not media.uri:
                    continue

                if not fallback_audio and media.default:
                    fallback_audio = [media]

                # if the media is "audoselect" and it better matches the users preferences, use that
                # instead of default
                if not default_audio and (media.autoselect and locale.equivalent(language=media.language)):
                    default_audio = [media]

                # select the first audio stream that matches the users explict language selection
                if (('*' in audio_select or media.language in audio_select or media.name in audio_select)
                        or ((not preferred_audio or media.default) and locale.explicit and locale.equivalent(
                            language=media.language))):
                    preferred_audio.append(media)

            # final fallback on the first audio stream listed
            fallback_audio = fallback_audio or (len(audio_streams) and audio_streams[0].uri and [audio_streams[0]])

            if playlist.stream_info.resolution:
                width, height = playlist.stream_info.resolution
                names["pixels"] = "{0}p".format(height)

            if playlist.stream_info.bandwidth:
                bw = playlist.stream_info.bandwidth

                if bw >= 1000:
                    names["bitrate"] = "{0}k".format(int(bw / 1000.0))
                else:
                    names["bitrate"] = "{0}k".format(bw / 1000.0)

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
                stream_name = "{0}{1}".format(name_prefix, stream_name)

            if stream_name in streams:  # rename duplicate streams
                stream_name = "{0}_alt".format(stream_name)
                num_alts = len(list(filter(lambda n: n.startswith(stream_name), streams.keys())))

                # We shouldn't need more than 2 alt streams
                if num_alts >= 2:
                    continue
                elif num_alts > 0:
                    stream_name = "{0}{1}".format(stream_name, num_alts + 1)

            if check_streams:
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

                stream = MuxedHLSStream(session_,
                                        video=playlist.uri,
                                        audio=[x.uri for x in external_audio if x.uri],
                                        url_master=url,
                                        force_restart=force_restart,
                                        start_offset=start_offset,
                                        duration=duration,
                                        **request_params)
            else:
                stream = cls(session_,
                             playlist.uri,
                             url_master=url,
                             force_restart=force_restart,
                             start_offset=start_offset,
                             duration=duration,
                             **request_params)
            streams[stream_name] = stream

        return streams
