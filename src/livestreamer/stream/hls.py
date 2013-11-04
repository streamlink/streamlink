import io

from collections import defaultdict, namedtuple
from time import time
from threading import Lock, Thread, Timer

try:
    from Crypto.Cipher import AES
    import struct

    def num_to_iv(n):
        return struct.pack(">8xq", n)

    CAN_DECRYPT = True
except ImportError:
    CAN_DECRYPT = False

from . import hls_playlist
from .stream import Stream
from .http import HTTPStream
from ..buffers import RingBuffer
from ..compat import queue
from ..exceptions import StreamError
from ..utils import urlget


Sequence = namedtuple("Sequence", "num segment")


class HLSStreamFiller(Thread):
    def __init__(self, stream):
        Thread.__init__(self)

        self.daemon = True
        self.queue = queue.Queue(maxsize=5)
        self.running = False
        self.stream = stream
        self.key_uri = None
        self.key_data = None
        self.byterange_offsets = defaultdict(int)

    def create_decryptor(self, key, sequence):
        if key.method == "NONE":
            return

        if key.method != "AES-128":
            raise StreamError("Unable to decrypt cipher {0}",
                              key.method)

        if not key.uri:
            raise StreamError("Missing URI to decryption key")

        if self.key_uri != key.uri:
            res = urlget(key.uri, exception=StreamError,
                         **self.stream.request_params)
            self.key_data = res.content
            self.key_uri = key.uri

        iv = key.iv or num_to_iv(sequence)
        return AES.new(self.key_data, AES.MODE_CBC, iv)

    def download_sequence(self, sequence):
        try:
            request_params = dict(self.stream.request_params)
            headers = request_params.pop("headers", {})
            if sequence.segment.byterange:
                bytes_start = self.byterange_offsets[sequence.segment.uri]
                if sequence.segment.byterange.offset is not None:
                    bytes_start = sequence.segment.byterange.offset

                bytes_end = bytes_start + min(sequence.segment.byterange.range - 1, 0)
                headers["Range"] = "bytes={0}-{1}".format(bytes_start,
                                                          bytes_end)
                self.byterange_offsets[sequence.segment.uri] = bytes_end + 1

            request_params["headers"] = headers
            res = urlget(sequence.segment.uri, stream=True,
                         exception=IOError, **request_params)
        except IOError as err:
            self.stream.logger.error("Failed to open sequence {0}: {1}",
                                     sequence.num, str(err))
            return

        try:
            if sequence.segment.key:
                decryptor = self.create_decryptor(sequence.segment.key,
                                                  sequence.num)
            else:
                decryptor = None
        except StreamError as err:
            self.stream.logger.error("Failed to create decryptor: {0}",
                                     err)
            return self.stop()

        while self.running:
            try:
                chunk = res.raw.read(8192)
            except IOError as err:
                self.stream.logger.error("Failed to read segment {0}: {1}",
                                         sequence.num, err)
                break

            if not chunk:
                self.stream.logger.debug("Download of segment {0} complete",
                                         sequence.num)
                break

            if decryptor:
                chunk = decryptor.decrypt(chunk)

            self.stream.buffer.write(chunk)

    def run(self):
        self.stream.logger.debug("Starting buffer filler thread")

        while self.running:
            try:
                sequence = self.queue.get(True, 5)
            except queue.Empty:
                continue

            self.download_sequence(sequence)

            if sequence.num == self.stream.playlist_end:
                break

        if self.stream.playlist_timer:
            self.stream.playlist_timer.cancel()

        self.stop()
        self.stream.logger.debug("Buffer filler thread completed")

    def start(self):
        self.running = True

        return Thread.start(self)

    def stop(self):
        self.running = False
        self.stream.buffer.close()


class HLSStreamIO(io.IOBase):
    def __init__(self, session_, url, timeout=60, **request_params):
        self.session = session_
        self.url = url
        self.timeout = timeout
        self.request_params = request_params

        self.logger = session_.logger.new_module("stream.hls")
        self.buffer = None

    def open(self):
        self.playlist_changed = False
        self.playlist_end = None
        self.playlist_sequences = []
        self.playlist_lock = Lock()
        self.playlist_minimal_reload_time = 15
        self.playlist_reload_time = 0
        self.playlist_timer = None

        self.sequence = -1

        self.buffer = RingBuffer(self.session.get_option("ringbuffer-size"))
        self.filler = HLSStreamFiller(self)
        self.filler.start()

        try:
            self.reload_playlist(silent=False, fillqueue=True)
        except StreamError:
            self.close()
            raise

        return self

    def close(self):
        self.filler.stop()

        if self.filler.is_alive():
            self.filler.join()

    def read(self, size=-1):
        if not self.buffer:
            return b""

        return self.buffer.read(size, block=self.filler.is_alive(),
                                timeout=self.timeout)

    def reload_playlist(self, silent=True, fillqueue=False):
        if not self.filler.running:
            return

        if self.playlist_end and self.sequence > self.playlist_end:
            return

        # Wait until buffer has room before requesting a new playlist
        self.buffer.wait_free()

        elapsed = time() - self.playlist_reload_time
        if elapsed > self.playlist_minimal_reload_time:
            try:
                self._reload_playlist()
            except IOError as err:
                if silent:
                    self.logger.error("Failed to reload playlist: {0}", str(err))
                else:
                    raise StreamError(str(err))

        if self.playlist_changed:
            self._queue_sequences(fillqueue)

        self.playlist_timer = Timer(1, self.reload_playlist)
        self.playlist_timer.daemon = True
        self.playlist_timer.start()

    def _reload_playlist(self):
        self.logger.debug("Reloading playlist")
        self.playlist_reload_time = time()

        res = urlget(self.url, exception=IOError, **self.request_params)
        playlist = hls_playlist.load(res.text, base_uri=self.url)

        media_sequence = playlist.media_sequence or 0
        sequences = [Sequence(media_sequence + i, s)
                     for i, s in enumerate(playlist.segments)]

        if sequences:
            return self._handle_sequences(playlist, sequences)

    def _handle_sequences(self, playlist, sequences):
        first_sequence, last_sequence = sequences[0], sequences[-1]

        # First playlist load
        if not self.playlist_timer:
            if playlist.iframes_only:
                raise StreamError("Streams containing I-frames only is "
                                  "not playable.")

            if (first_sequence.segment.key and
                first_sequence.segment.key.method != "NONE"):

                self.logger.debug("Segments in this stream are encrypted")
                if not CAN_DECRYPT:
                    raise StreamError("Need pyCrypto installed to decrypt this stream")

        self.playlist_changed = ([s.num for s in self.playlist_sequences] !=
                                 [s.num for s in sequences])
        self.playlist_minimal_reload_time = (playlist.target_duration or
                                             last_sequence.segment.duration)
        self.playlist_sequences = sequences

        if not self.playlist_changed:
            self.playlist_minimal_reload_time = max(self.playlist_minimal_reload_time / 2, 1)

        if playlist.is_endlist:
            self.playlist_end = last_sequence.num

        if self.sequence < 0:
            if self.playlist_end is None:
                edge_sequence = sequences[-(min(len(sequences), 3))]
                self.sequence = edge_sequence.num
            else:
                self.sequence = first_sequence.num
        elif first_sequence.num == 0 and self.sequence > 0:
            # The sequence number has wrapped around. This should probably not
            # happen, but it wasn't until draft-pantos-http-live-streaming-12
            # that it was explicitly stated that sequence numbers should never
            # decrease.
            self.sequence = first_sequence.num

    def _queue_sequences(self, fillqueue=False):
        for i, sequence in enumerate(self.playlist_sequences):
            if not self.filler.running:
                break

            if fillqueue and i == self.filler.queue.maxsize:
                break

            if sequence.num >= self.sequence:
                self.logger.debug("Adding sequence {0} to queue",
                                  sequence.num)

                while self.filler.running:
                    try:
                        self.filler.queue.put(sequence, True, 5)
                        break
                    except queue.Full:
                        continue

                self.sequence = sequence.num + 1


class HLSStream(HTTPStream):
    """Implementation of the Apple HTTP Live Streaming protocol

    *Attributes:*

    - :attr:`url` The URL to the HLS playlist.
    - :attr:`args` A :class:`dict` containing keyword arguments passed
                   to :meth:`requests.request`, such as headers and
                   cookies.

    .. versionchanged:: 1.7.0
       Added *args* attribute.

    """

    __shortname__ = "hls"

    def __init__(self, session_, url, **args):
        Stream.__init__(self, session_)

        self.args = dict(url=url, **args)

    def __repr__(self):
        return "<HLSStream({0!r})>".format(self.url)

    def __json__(self):
        json = HTTPStream.__json__(self)

        # Pretty sure HLS is GET only.
        del json["method"]
        del json["body"]

        return json

    def open(self):
        fd = HLSStreamIO(self.session, **self.args)

        return fd.open()

    @classmethod
    def parse_variant_playlist(cls, session_, url, namekey="name",
                               nameprefix="", **request_params):
        res = urlget(url, exception=IOError, **request_params)
        parser = hls_playlist.load(res.text, base_uri=url)

        streams = {}
        for playlist in filter(lambda p: not p.is_iframe, parser.playlists):
            names = dict(name=None, pixels=None, bitrate=None)

            for media in playlist.media:
                if media.type == "VIDEO" and media.name:
                    names["name"] = media.name

            if playlist.stream_info.resolution:
                width, height = playlist.stream_info.resolution
                names["pixels"] = "{0}p".format(height)

            if playlist.stream_info.bandwidth:
                bw = playlist.stream_info.bandwidth

                if bw >= 1000:
                    names["bitrate"] = "{0}k".format(int(bw/1000.0))
                else:
                    names["bitrate"] = "{0}k".format(bw/1000.0)

            stream_name = (names.get(namekey) or names.get("name") or
                           names.get("pixels") or names.get("bitrate"))

            if not stream_name:
                continue

            stream = HLSStream(session_, playlist.uri, **request_params)
            streams[nameprefix + stream_name] = stream

        return streams
