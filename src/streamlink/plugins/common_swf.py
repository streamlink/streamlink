from collections import namedtuple
from io import BytesIO

from streamlink.packages.flashmedia.types import U16LE, U32LE
from streamlink.utils import swfdecompress

__all__ = ["parse_swf"]

Rect = namedtuple("Rect", "data")
Tag = namedtuple("Tag", "type data")
SWF = namedtuple("SWF", "frame_size frame_rate frame_count tags")


def read_rect(fd):
    header = ord(fd.read(1))
    nbits = header >> 3
    nbytes = int(((5 + 4 * nbits) + 7) / 8)
    data = fd.read(nbytes - 1)

    return Rect(data)


def read_tag(fd):
    header = U16LE.read(fd)
    tag_type = header >> 6
    tag_length = header & 0x3f
    if tag_length == 0x3f:
        tag_length = U32LE.read(fd)

    tag_data = fd.read(tag_length)

    return Tag(tag_type, tag_data)


def read_tags(fd):
    while True:
        try:
            yield read_tag(fd)
        except OSError:
            break


def parse_swf(data):
    data = swfdecompress(data)
    fd = BytesIO(data[8:])
    frame_size = read_rect(fd)
    frame_rate = U16LE.read(fd)
    frame_count = U16LE.read(fd)
    tags = list(read_tags(fd))

    return SWF(frame_size, frame_rate, frame_count, tags)
