from . import Stream, StreamError
from ..utils import urlget, RingBuffer, absolute_url
from ..compat import urljoin, queue

from time import time, sleep
from threading import Lock, Thread, Timer

import io
import os.path
import re

try:
    from Crypto.Cipher import AES
    import struct

    def num_to_iv(n):
        return struct.pack(">8xq", n)

    CAN_DECRYPT = True

except ImportError:
    CAN_DECRYPT = False


def parse_m3u_attributes(data):
    attr = re.findall("([A-Z\-]+)=(\d+\.\d+|0x[0-9A-z]+|\d+x\d+|\d+|\"(.+?)\"|[0-9A-z\-]+)", data)
    rval = {}

    for key, val, strval in attr:
        if len(strval) > 0:
            rval[key] = strval
        else:
            rval[key] = val

    if len(rval) > 0:
        return rval

    return data

def parse_m3u_tag(data):
    key = data[1:]
    value = None
    valpos = data.find(":")

    if valpos > 0:
        key = data[1:valpos]
        value = data[valpos+1:]

    return (key, value)

def parse_m3u(data):
    lines = [line for line in data.splitlines() if len(line) > 0]
    tags = {}
    entries = []

    lasttag = None

    for i, line in enumerate(lines):
        if line.startswith("#EXT"):
            (key, value) = parse_m3u_tag(line)

            if value is not None:
                if key == "EXTINF":
                    duration, title = value.split(",")
                    value = (float(duration), title)
                else:
                    value = parse_m3u_attributes(value)

            if key in tags:
                tags[key].append(value)
            else:
                tags[key] = [value]

            lasttag = (key, value)
        else:
            entry = { "url": line, "tag": lasttag }
            entries.append(entry)

    return (tags, entries)


class HLSStreamFiller(Thread):
    def __init__(self, stream):
        Thread.__init__(self)

        self.daemon = True
        self.queue = queue.Queue(maxsize=5)
        self.running = False
        self.stream = stream

    def download_sequence(self, entry):
        try:
            res = urlget(entry["url"], stream=True,
                         exception=IOError)
        except IOError as err:
            self.stream.logger.error("Failed to open sequence {0}: {1}",
                                     entry["sequence"], str(err))
            return

        if self.stream.decryptor_key:
            iv = num_to_iv(entry["sequence"])
            decryptor = AES.new(self.stream.decryptor_key, AES.MODE_CBC, iv)
        else:
            decryptor = None

        while self.running:
            try:
                chunk = res.raw.read(8192)
            except IOError as err:
                self.stream.logger.error("Failed to read sequence {0}: {1}",
                                         entry["sequence"], str(err))
                break

            if len(chunk) == 0:
                self.stream.logger.debug("Download of sequence {0} complete", entry["sequence"])
                break

            if decryptor:
                chunk = decryptor.decrypt(chunk)

            self.stream.buffer.write(chunk)

    def run(self):
        self.stream.logger.debug("Starting buffer filler thread")

        while self.running:
            try:
                entry = self.queue.get(True, 5)
            except queue.Empty:
                continue

            self.download_sequence(entry)

            if entry["sequence"] == self.stream.playlist_end:
                break

        if self.stream.playlist_timer:
            self.stream.playlist_timer.cancel()

        self.running = False
        self.stream.buffer.close()
        self.stream.logger.debug("Buffer filler thread completed")

    def start(self):
        self.running = True

        return Thread.start(self)

    def stop(self):
        self.running = False


class HLSStreamIO(io.IOBase):
    def __init__(self, session, url, timeout=60):
        self.session = session
        self.url = url
        self.timeout = timeout

        self.logger = session.logger.new_module("stream.hls")
        self.buffer = None

    def open(self):
        self.playlist_changed = False
        self.playlist_end = None
        self.playlist_entries = []
        self.playlist_lock = Lock()
        self.playlist_minimal_reload_time = 15
        self.playlist_reload_time = 0
        self.playlist_timer = None

        self.decryptor_key = None
        self.sequence = -1

        self.buffer = RingBuffer(self.session.get_option("ringbuffer-size"))
        self.filler = HLSStreamFiller(self)
        self.filler.start()
        self.reload_playlist(silent=False, fillqueue=True)

        return self

    def close(self):
        self.filler.stop()

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

        res = urlget(self.url, exception=IOError)
        (tags, entries) = parse_m3u(res.text)

        if "EXT-X-MEDIA-SEQUENCE" in tags:
            sequence = int(tags["EXT-X-MEDIA-SEQUENCE"][0])
        else:
            sequence = 0

        if "EXT-X-KEY" in tags and tags["EXT-X-KEY"][0]["METHOD"] != "NONE":
            self.logger.debug("Sequences in this playlist are encrypted")

            if not CAN_DECRYPT:
                raise StreamError("Need pyCrypto installed to decrypt data")

            if tags["EXT-X-KEY"][0]["METHOD"] != "AES-128":
                raise StreamError("Unable to decrypt cipher {0}", tags["EXT-X-KEY"][0]["METHOD"][0])

            if not "URI" in tags["EXT-X-KEY"][0]:
                raise StreamError("Missing URI to decryption key")

            res = urlget(tags["EXT-X-KEY"][0]["URI"], exception=StreamError)
            self.decryptor_key = res.content

        for i, entry in enumerate(entries):
            entry["sequence"] = sequence + i
            entry["url"] = absolute_url(self.url, entry["url"])

        self.playlist_entries = entries

        if len(entries) == 0:
            return

        firstentry = entries[0]
        lastentry = entries[-1]

        if "EXT-X-ENDLIST" in tags:
            self.playlist_end = lastentry["sequence"]

        self.playlist_changed = (self.sequence - 1) != lastentry["sequence"]

        if not self.playlist_changed:
            self.playlist_minimal_reload_time = max(self.playlist_minimal_reload_time / 2, 1)

        if self.sequence < firstentry["sequence"] or (self.sequence - 1) > lastentry["sequence"]:
            totalentries = len(entries)

            if totalentries > 3 and self.playlist_end is None:
                self.sequence = sequence + (totalentries - 3)
            else:
                self.sequence = sequence

    def _queue_sequences(self, fillqueue=False):
        if len(self.playlist_entries) == 0:
            return

        for i, entry in enumerate(self.playlist_entries):
            if fillqueue and i == self.filler.queue.maxsize:
                break

            if entry["sequence"] == self.sequence:
                self.logger.debug("Adding sequence {0} to queue", entry["sequence"])

                while self.filler.running:
                    try:
                        self.filler.queue.put(entry, True, 5)
                        break
                    except queue.Full:
                        continue

                self.sequence += 1

            if entry["tag"][0] == "EXTINF":
                duration = entry["tag"][1][0]
                self.playlist_minimal_reload_time = duration

        self.playlist_changed = (self.sequence - 1) != self.playlist_entries[-1]["sequence"]


class HLSStream(Stream):
    __shortname__ = "hls"

    def __init__(self, session, url):
        Stream.__init__(self, session)

        self.url = url

    def __repr__(self):
        return "<HLSStream({0!r})>".format(self.url)

    def __json__(self):
        return dict(type=HLSStream.shortname(),
                    url=self.url)

    def open(self):
        fd = HLSStreamIO(self.session, self.url)

        return fd.open()

    @classmethod
    def parse_variant_playlist(cls, session, url, **params):
        res = urlget(url, exception=IOError, **params)
        streams = {}

        (tags, entries) = parse_m3u(res.text)

        for entry in entries:
            (tag, value) = entry["tag"]

            if tag != "EXT-X-STREAM-INF":
                continue

            if "EXT-X-MEDIA" in tags:
                for media in tags["EXT-X-MEDIA"]:
                    key = media["TYPE"]

                    if key in value and value[key] == media["GROUP-ID"]:
                        value.update(media)

            if "NAME" in value:
                quality = value["NAME"]
            elif "RESOLUTION" in value:
                quality = value["RESOLUTION"].split("x")[1] + "p"
            elif "BANDWIDTH" in value:
                bw = int(value["BANDWIDTH"])

                if bw > 1000:
                    quality = str(int(bw/1000.0)) + "k"
                else:
                    quality = str(bw/1000.0) + "k"
            else:
                continue

            stream = HLSStream(session, absolute_url(url, entry["url"]))
            streams[quality] = stream

        return streams
