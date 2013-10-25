import re

from io import BytesIO

from livestreamer.compat import is_py2, range
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget

from livestreamer.packages.flashmedia.types import U8, U32LE
from livestreamer.plugin.api.support_plugin import common_swf as swfparser


# This token extraction and decryption code has been ported from
# secureToken.d which was created by DEAD_MAN_WALKING of WiZiWiG forums.
class Decryptor(object):
    def __init__(self, key):
        key = bytes_list(key)
        data = list(range(256))

        b, n = 0, len(key)
        for i in range(256):
            b += (data[i] + key[i%n])
            b &= 0xff
            data[i], data[b] = data[b], data[i]

        self.c1 = self.c2 = 0
        self.data = data

    def decrypt(self, data):
        data = bytes_list(data)

        for i, c in enumerate(data):
            data[i] ^= self.next_byte()

        return "".join(chr(c) for c in data)

    def next_byte(self):
        self.c1 += 1
        self.c2 += self.data[self.c1]
        self.c2 &= 0xff
        self.data[self.c1], self.data[self.c2] = (self.data[self.c2],
                                                  self.data[self.c1])

        return self.data[(self.data[self.c1] + self.data[self.c2]) & 0xff]


def bytes_list(val):
    if is_py2:
        return [ord(c) for c in val]
    else:
        return list(val)


def extract_bin(tag):
    tag_bin = tag.data[6:]

    if len(tag_bin) > 4 and tag_bin[:3] != b"CWS":
        return tag_bin


def extract_bins(swf):
    for tag in swf.tags:
        if tag.type == 87 and len(tag.data) >= 6:
            tag_bin = extract_bin(tag)
            if tag_bin:
                yield tag_bin


def extract_strings(data, keys):
    fd = BytesIO(keys)
    keys = [fd.read(16) for i in range(U8.read(fd))]
    if not keys:
        return

    fd = BytesIO(data)
    for i in range(U32LE.read(fd)):
        msg = fd.read(U32LE.read(fd))
        key = keys[i % len(keys)]

        return Decryptor(key).decrypt(msg)


class ILive(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return "ilive.to" in url

    def _extract_token(self, swf):
        res = urlget(swf)
        swf = swfparser.parse_swf(res.content)
        bins = list(extract_bins(swf))

        for tag_bin in bins:
            for tag_bin2 in filter(lambda b: b != tag_bin, bins):
                token = extract_strings(tag_bin, tag_bin2)
                if token:
                    return token

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        res = urlget(self.url)

        match = re.search("flashplayer: \"(.+.swf)\".+streamer: \"(.+)\".+"
                          "file: \"(.+).flv\"", res.text, re.DOTALL)
        if not match:
            return

        params = {
            "rtmp": match.group(2),
            "pageUrl": self.url,
            "swfVfy": match.group(1),
            "playpath" : match.group(3),
            "token": self._extract_token(match.group(1)),
            "live": True
        }

        streams = {}
        streams["live"] = RTMPStream(self.session, params)

        return streams


__plugin__ = ILive
