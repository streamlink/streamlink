from . import Stream, StreamError
from ..utils import urlget

from time import time, sleep

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
    attr = re.findall("([A-Z\-]+)=(\d+\.\d+|0x[0-9A-z]+|\d+x\d+|\d+|\"(.+)\"|[0-9A-z\-]+)", data)
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

            tags[key] = value
            lasttag = (key, value)
        else:
            entry = { "url": line, "tag": lasttag }
            entries.append(entry)

    return (tags, entries)

class HLSStream(Stream):
    def __init__(self, session, url):
        Stream.__init__(self, session)

        self.url = url
        self.playlist = {}
        self.playlist_reload_time = 0
        self.playlist_minimal_reload_time = 15
        self.playlist_end = False
        self.entry = None
        self.decryptor = None
        self.decryptor_key = None
        self.decryptor_iv = None
        self.fd = None
        self.sequence = 0
        self.logger = session.logger.new_module("stream.hls")

    def open(self):
        return self

    def read(self, size=-1):
        if self.entry is None:
            try:
                self._next_entry()
            except IOError:
                return b""

        data = self.fd.read(size)

        if len(data) == 0:
            self._next_entry()
            return self.read(size)

        if self.decryptor:
            data = self.decryptor.decrypt(data)

        return data

    def _next_entry(self):
        if len(self.playlist) == 0:
            self._reload_playlist()

        # Periodic reload is not fatal if it fails
        elapsed = time() - self.playlist_reload_time
        if elapsed > self.playlist_minimal_reload_time:
            try:
                self._reload_playlist()
            except IOError:
                pass

        if not self.sequence in self.playlist:
            if self.playlist_end:
                # Last playlist is over
                raise IOError("End of stream")
            else:
                self.logger.debug("Next sequence not available yet")
                sleep(1)
                return self._next_entry()

        self.entry = self.playlist[self.sequence]

        self.logger.debug("Next entry: {0}", self.entry)

        res = urlget(self.entry["url"], prefetch=False,
                     exception=IOError)

        self.playlist[self.sequence] = None

        if self.decryptor_key:
            if not self.decryptor_iv:
                iv = num_to_iv(self.sequence)
            else:
                iv = num_to_iv(self.decryptor_iv)

            self.decryptor = AES.new(self.decryptor_key, AES.MODE_CBC, iv)

        self.fd = res.raw
        self.sequence += 1

    def _reload_playlist(self):
        if self.playlist_end:
            return

        self.logger.debug("Reloading playlist")

        res = urlget(self.url, exception=IOError)

        (tags, entries) = parse_m3u(res.text)

        if "EXT-X-ENDLIST" in tags:
            self.playlist_end = True

        if "EXT-X-MEDIA-SEQUENCE" in tags:
            sequence = int(tags["EXT-X-MEDIA-SEQUENCE"])
        else:
            sequence = 0

        if "EXT-X-KEY" in tags and tags["EXT-X-KEY"]["METHOD"] != "NONE":
            if not CAN_DECRYPT:
                self.logger.error("Need pyCrypto installed to decrypt data")
                raise IOError

            if tags["EXT-X-KEY"]["METHOD"] != "AES-128":
                self.logger.error("Unable to decrypt cipher {0}", tags["EXT-X-KEY"]["METHOD"])
                raise IOError

            if not "URI" in tags["EXT-X-KEY"]:
                self.logger.error("Missing URI to decryption key")
                raise IOError

            res = urlget(tags["EXT-X-KEY"]["URI"], exception=IOError)
            self.decryptor_key = res.content

        for i, entry in enumerate(entries):
            self.playlist[sequence + i] = entry

            if entry["tag"][0] == "EXTINF":
                duration = entry["tag"][1][0]
                self.playlist_minimal_reload_time = duration

        if self.sequence == 0:
            self.sequence = sequence

        self.playlist_reload_time = time()

    @classmethod
    def parse_variant_playlist(cls, session, url):
        res = urlget(url, exception=IOError)
        streams = {}

        (tags, entries) = parse_m3u(res.text)

        for entry in entries:
            (tag, value) = entry["tag"]

            if tag != "EXT-X-STREAM-INF":
                continue

            if not "RESOLUTION" in value:
                continue

            quality = value["RESOLUTION"].split("x")[1] + "p"
            stream = HLSStream(session, entry["url"])

            streams[quality] = stream

        return streams
