import logging
import re
import struct

from collections import defaultdict, namedtuple
from Crypto.Cipher import AES

from streamlink.exceptions import StreamError
from streamlink.stream import hls_playlist
from streamlink.stream.ffmpegmux import FFMPEGMuxer, MuxedStream
from streamlink.stream.http import HTTPStream
from streamlink.stream.segmented import (SegmentedStreamReader,
                                         SegmentedStreamWriter,
                                         SegmentedStreamWorker)

log = logging.getLogger(__name__)
Sequence = namedtuple("Sequence", "num segment")


def num_to_iv(n):
    return struct.pack(">8xq", n)


def pkcs7_decode(paddedData, keySize=16):
    '''
    Remove the PKCS#7 padding
    '''
    # Use ord + [-1:] to support both python 2 and 3
    val = ord(paddedData[-1:])
    if val > keySize:
        raise StreamError("Input is not padded or padding is corrupt, got padding size of {0}".format(val))

    return paddedData[:-val]


class HLSStreamWriter(SegmentedStreamWriter):
    def __init__(self, reader, *args, **kwargs):
        options = reader.stream.session.options
        kwargs["retries"] = options.get("hls-segment-attempts")
        kwargs["threads"] = options.get("hls-segment-threads")
        kwargs["timeout"] = options.get("hls-segment-timeout")
        kwargs["ignore_names"] = options.get("hls-segment-ignore-names")
        SegmentedStreamWriter.__init__(self, reader, *args, **kwargs)

        self.byterange_offsets = defaultdict(int)
        self.key_data = None
        self.key_uri = None
        if self.ignore_names:
            # creates a regex from a list of segment names,
            # this will be used to ignore segments.
            self.ignore_names = list(set(self.ignore_names))
            self.ignore_names = "|".join(list(map(re.escape, self.ignore_names)))
            self.ignore_names_re = re.compile(r"(?:{blacklist})\.ts".format(
                blacklist=self.ignore_names), re.IGNORECASE)

    def create_decryptor(self, key, sequence):
        if key.method != "AES-128":
            raise StreamError("Unable to decrypt cipher {0}", key.method)

        if not key.uri:
            raise StreamError("Missing URI to decryption key")

        if self.key_uri != key.uri:
            res = self.session.http.get(key.uri, exception=StreamError,
                                        retries=self.retries,
                                        **self.reader.request_params)
            self.key_data = res.content
            self.key_uri = key.uri

        iv = key.iv or num_to_iv(sequence)

        # Pad IV if needed
        iv = b"\x00" * (16 - len(iv)) + iv

        return AES.new(self.key_data, AES.MODE_CBC, iv)

    def create_request_params(self, sequence):
        request_params = dict(self.reader.request_params)
        headers = request_params.pop("headers", {})

        if sequence.segment.byterange:
            bytes_start = self.byterange_offsets[sequence.segment.uri]
            if sequence.segment.byterange.offset is not None:
                bytes_start = sequence.segment.byterange.offset

            bytes_len = max(sequence.segment.byterange.range - 1, 0)
            bytes_end = bytes_start + bytes_len
            headers["Range"] = "bytes={0}-{1}".format(bytes_start, bytes_end)
            self.byterange_offsets[sequence.segment.uri] = bytes_end + 1

        request_params["headers"] = headers

        return request_params

    def fetch(self, sequence, retries=None):
        if self.closed or not retries:
            return

        try:
            request_params = self.create_request_params(sequence)
            # skip ignored segment names
            if self.ignore_names and self.ignore_names_re.search(sequence.segment.uri):
                log.debug("Skipping segment {0}".format(sequence.num))
                return

            return self.session.http.get(sequence.segment.uri,
                                         timeout=self.timeout,
                                         exception=StreamError,
                                         retries=self.retries,
                                         **request_params)
        except StreamError as err:
            log.error("Failed to open segment {0}: {1}", sequence.num, err)
            return

    def write(self, sequence, res, chunk_size=8192):
        if sequence.segment.key and sequence.segment.key.method != "NONE":
            try:
                decryptor = self.create_decryptor(sequence.segment.key,
                                                  sequence.num)
            except StreamError as err:
                log.error("Failed to create decryptor: {0}", err)
                self.close()
                return

            data = res.content
            # If the input data is not a multiple of 16, cut off any garbage
            garbage_len = len(data) % 16
            if garbage_len:
                log.debug("Cutting off {0} bytes of garbage "
                          "before decrypting", garbage_len)
                decrypted_chunk = decryptor.decrypt(data[:-garbage_len])
            else:
                decrypted_chunk = decryptor.decrypt(data)

            self.reader.buffer.write(pkcs7_decode(decrypted_chunk))
        else:
            for chunk in res.iter_content(chunk_size):
                self.reader.buffer.write(chunk)

        log.debug("Download of segment {0} complete", sequence.num)


class HLSStreamWorker(SegmentedStreamWorker):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWorker.__init__(self, *args, **kwargs)
        self.stream = self.reader.stream

        self.playlist_changed = False
        self.playlist_end = None
        self.playlist_sequence = -1
        self.playlist_sequences = []
        self.playlist_reload_time = 15
        self.live_edge = self.session.options.get("hls-live-edge")
        self.playlist_reload_retries = self.session.options.get("hls-playlist-reload-attempts")
        self.duration_offset_start = int(self.stream.start_offset + (self.session.options.get("hls-start-offset") or 0))
        self.duration_limit = self.stream.duration or (
            int(self.session.options.get("hls-duration")) if self.session.options.get("hls-duration") else None)
        self.hls_live_restart = self.stream.force_restart or self.session.options.get("hls-live-restart")

        self.reload_playlist()

        if self.playlist_end is None:
            if self.duration_offset_start > 0:
                log.debug("Time offsets negative for live streams, skipping back {0} seconds",
                          self.duration_offset_start)
            # live playlist, force offset durations back to None
            self.duration_offset_start = -self.duration_offset_start

        if self.duration_offset_start != 0:
            self.playlist_sequence = self.duration_to_sequence(self.duration_offset_start, self.playlist_sequences)

        if self.playlist_sequences:
            log.debug("First Sequence: {0}; Last Sequence: {1}",
                      self.playlist_sequences[0].num, self.playlist_sequences[-1].num)
            log.debug("Start offset: {0}; Duration: {1}; Start Sequence: {2}; End Sequence: {3}",
                      self.duration_offset_start, self.duration_limit,
                      self.playlist_sequence, self.playlist_end)

    def reload_playlist(self):
        if self.closed:
            return

        self.reader.buffer.wait_free()
        log.debug("Reloading playlist")
        res = self.session.http.get(self.stream.url,
                                    exception=StreamError,
                                    retries=self.playlist_reload_retries,
                                    **self.reader.request_params)
        try:
            playlist = hls_playlist.load(res.text, res.url)
        except ValueError as err:
            raise StreamError(err)

        if playlist.is_master:
            raise StreamError("Attempted to play a variant playlist, use "
                              "'hls://{0}' instead".format(self.stream.url))

        if playlist.iframes_only:
            raise StreamError("Streams containing I-frames only is not playable")

        media_sequence = playlist.media_sequence or 0
        sequences = [Sequence(media_sequence + i, s)
                     for i, s in enumerate(playlist.segments)]

        if sequences:
            self.process_sequences(playlist, sequences)

    def process_sequences(self, playlist, sequences):
        first_sequence, last_sequence = sequences[0], sequences[-1]

        if first_sequence.segment.key and first_sequence.segment.key.method != "NONE":
            log.debug("Segments in this playlist are encrypted")

        self.playlist_changed = ([s.num for s in self.playlist_sequences] !=
                                 [s.num for s in sequences])
        self.playlist_reload_time = (playlist.target_duration or
                                     last_sequence.segment.duration)
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

    def valid_sequence(self, sequence):
        return sequence.num >= self.playlist_sequence

    def duration_to_sequence(self, duration, sequences):
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
        total_duration = 0
        while not self.closed:
            for sequence in filter(self.valid_sequence, self.playlist_sequences):
                log.debug("Adding segment {0} to queue", sequence.num)
                yield sequence
                total_duration += sequence.segment.duration
                if self.duration_limit and total_duration >= self.duration_limit:
                    log.info("Stopping stream early after {0}".format(self.duration_limit))
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
                    log.warning("Failed to reload playlist: {0}", err)


class HLSStreamReader(SegmentedStreamReader):
    __worker__ = HLSStreamWorker
    __writer__ = HLSStreamWriter

    def __init__(self, stream, *args, **kwargs):
        SegmentedStreamReader.__init__(self, stream, *args, **kwargs)
        self.request_params = dict(stream.args)
        self.timeout = stream.session.options.get("hls-timeout")

        # These params are reserved for internal use
        self.request_params.pop("exception", None)
        self.request_params.pop("stream", None)
        self.request_params.pop("timeout", None)
        self.request_params.pop("url", None)


class MuxedHLSStream(MuxedStream):
    __shortname__ = "hls-multi"

    def __init__(self, session, video, audio, force_restart=False, ffmpeg_options=None, **args):
        tracks = [video]
        if audio:
            if isinstance(audio, list):
                tracks.extend(audio)
            else:
                tracks.append(audio)
        substreams = map(lambda url: HLSStream(session, url, force_restart=force_restart, **args), tracks)
        ffmpeg_options = ffmpeg_options or {}

        super(MuxedHLSStream, self).__init__(session, *substreams, format="mpegts", **ffmpeg_options)


class HLSStream(HTTPStream):
    """Implementation of the Apple HTTP Live Streaming protocol

    *Attributes:*

    - :attr:`url` The URL to the HLS playlist.
    - :attr:`args` A :class:`dict` containing keyword arguments passed
      to :meth:`requests.request`, such as headers and cookies.

    .. versionchanged:: 1.7.0
       Added *args* attribute.

    """

    __shortname__ = "hls"

    def __init__(self, session_, url, force_restart=False, start_offset=0, duration=None, **args):
        HTTPStream.__init__(self, session_, url, **args)
        self.force_restart = force_restart
        self.start_offset = start_offset
        self.duration = duration

    def __repr__(self):
        return "<HLSStream({0!r})>".format(self.url)

    def __json__(self):
        json = HTTPStream.__json__(self)

        # Pretty sure HLS is GET only.
        del json["method"]
        del json["body"]

        return json

    def open(self):
        reader = HLSStreamReader(self)
        reader.open()

        return reader

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
        # Backwards compatibility with "namekey" and "nameprefix" params.
        name_key = request_params.pop("namekey", name_key)
        name_prefix = request_params.pop("nameprefix", name_prefix)
        audio_select = session_.options.get("hls-audio-select") or []

        res = session_.http.get(url, exception=IOError, **request_params)

        try:
            parser = hls_playlist.load(res.text, base_uri=res.url)
        except ValueError as err:
            raise IOError("Failed to parse playlist: {0}".format(err))

        streams = {}
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
                if (('*' in audio_select or media.language in audio_select or media.name in audio_select) or
                        ((not preferred_audio or media.default) and locale.explicit and locale.equivalent(
                            language=media.language))):
                    preferred_audio.append(media)

            # final fallback on the first audio stream listed
            fallback_audio = fallback_audio or (len(audio_streams) and
                                                audio_streams[0].uri and [audio_streams[0]])

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
                stream_name = (names.get(name_key) or names.get("name") or
                               names.get("pixels") or names.get("bitrate"))

            if not stream_name:
                continue
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
                    "(language={0}, name={1})".format(x.language, (x.name or "N/A"))
                    for x in external_audio
                ])
                log.debug("Using external audio tracks for stream {0} {1}", name_prefix + stream_name,
                          external_audio_msg)

                stream = MuxedHLSStream(session_,
                                        video=playlist.uri,
                                        audio=[x.uri for x in external_audio if x.uri],
                                        force_restart=force_restart,
                                        start_offset=start_offset,
                                        duration=duration,
                                        **request_params)
            else:
                stream = HLSStream(session_, playlist.uri, force_restart=force_restart,
                                   start_offset=start_offset, duration=duration, **request_params)
            streams[name_prefix + stream_name] = stream

        return streams
