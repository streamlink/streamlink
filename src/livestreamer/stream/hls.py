from . import Stream, StreamError
from ..utils import urlget, RingBuffer
from ..compat import urljoin, queue

from time import time, sleep
from threading import Lock, Thread, Timer

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
        self.queue = queue.Queue()
        self.stream = stream

    def download_sequence(self, entry):
        try:
            res = urlget(entry["url"], prefetch=False,
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

        while True:
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

        while True:
            entry = self.queue.get()
            self.download_sequence(entry)

            if entry["sequence"] == self.stream.playlist_end:
                break

        self.stream.logger.debug("Buffer filler thread completed")
        self.stream.playlist_timer.cancel()

class HLSStream(Stream):
    def __init__(self, session, url, timeout=60):
        Stream.__init__(self, session)

        self.url = url
        self.timeout = timeout
        self.logger = session.logger.new_module("stream.hls")
        self.buffer = None

    def open(self):
        self.playlist_end = None
        self.playlist_lock = Lock()
        self.playlist_minimal_reload_time = 15
        self.playlist_reload_time = 0

        self.decryptor_key = None
        self.sequence = -1

        self.buffer = RingBuffer()
        self.filler = HLSStreamFiller(self)
        self.filler.start()
        self.check_playlist(silent=False)

        return self

    def read(self, size=-1):
        if not self.buffer:
            return b""

        while self.buffer.length == 0 and self.filler.is_alive():
            if self.buffer.elapsed_since_write() > self.timeout:
                raise IOError("Read timeout")

            sleep(0.10)

        return self.buffer.read(size)

    def check_playlist(self, silent=True):
        if self.playlist_end is not None:
            return

        next_check_time = 1

        with self.playlist_lock:
            # Periodic reload is not fatal if it fails
            elapsed = time() - self.playlist_reload_time
            if elapsed > self.playlist_minimal_reload_time:
                if silent:
                    try:
                        self._reload_playlist()
                    except IOError as err:
                        self.logger.error("Failed to reload playlist: {0}", str(err))
                        next_check_time = self.playlist_minimal_reload_time
                else:
                    self._reload_playlist()

            self.playlist_timer = Timer(next_check_time, self.check_playlist)
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

        if len(entries) == 0:
            return

        for i, entry in enumerate(entries):
            entry["sequence"] = sequence + i
            entry["url"] = self._relative_url(entry["url"])

        if "EXT-X-ENDLIST" in tags:
            self.playlist_end = entries[-1]["sequence"]

        if self.sequence < entries[0]["sequence"] or (self.sequence-1) > entries[-1]["sequence"]:
            totalentries = len(entries)

            if totalentries > 3 and self.playlist_end is None:
                self.sequence = sequence + (totalentries - 3)
            else:
                self.sequence = sequence

        playlistchanged = False
        for entry in entries:
            if entry["sequence"] == self.sequence:
                self.logger.debug("Adding sequence {0} to queue", entry["sequence"])
                self.filler.queue.put(entry)
                self.sequence += 1
                playlistchanged = True

            if entry["tag"][0] == "EXTINF":
                duration = entry["tag"][1][0]
                self.playlist_minimal_reload_time = duration

        if not playlistchanged:
            self.playlist_minimal_reload_time /= 2

    def _relative_url(self, url):
        if not url.startswith("http"):
            return urljoin(self.url, url)
        else:
            return url

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

            stream = HLSStream(session, entry["url"])
            streams[quality] = stream

        return streams
