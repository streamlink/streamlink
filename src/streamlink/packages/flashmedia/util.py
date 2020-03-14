from .compat import bytes, is_py2, string_types

import struct


def byte(ordinal):
    if isinstance(ordinal, string_types):
        ordinal = ord(ordinal)

    return bytes((ordinal,))


class flagproperty(object):
    def __init__(self, flags, attr, boolean=False):
        self.flags = flags
        self.attr = attr
        self.boolean = boolean

    def __get__(self, obj, cls):
        flags = getattr(obj, self.flags)
        val = getattr(flags.bit, self.attr)

        if self.boolean:
            val = bool(val)

        return val

    def __set__(self, obj, val):
        flags = getattr(obj, self.flags)
        setattr(flags.bit, self.attr, int(val))


def lang_to_iso639(lang):
    res = [0, 0, 0]

    for i in reversed(range(3)):
        res[i] = chr(0x60 + (lang & 0x1f))
        lang = lang >> 5

    return "".join(res)


def iso639_to_lang(iso639):
    res = 0

    for i in range(3):
        c = ord(iso639[i]) - 0x60
        res = res << 5
        res = res | c

    return res


def pack_many_into(buf, offset, types, values):
    for packer, value in zip(types, values):
        packer.pack_into(buf, offset, value)
        offset += packer.size

    return offset


def pack_bytes_into(buf, offset, data):
    size = len(data)
    fmt = str(size) + "s"
    struct.pack_into(fmt, buf, offset, data)

    return offset + size


def unpack_many_from(buf, offset, types):
    rval = tuple()

    for unpacker in types:
        rval += unpacker.unpack_from(buf, offset)
        offset += unpacker.size

    return rval


def chunked_read(fd, length, chunk_size=8192, exception=IOError):
    chunks = []
    data_left = length

    while data_left > 0:
        try:
            data = fd.read(min(8192, data_left))
        except IOError as err:
            raise exception("Failed to read data: {0}".format(str(err)))

        if not data:
            raise exception("End of stream before required data could be read")

        data_left -= len(data)
        chunks.append(data)

    return b"".join(chunks)


__all__ = ["byte", "flagproperty", "lang_to_iso639",
           "iso639_to_lang", "pack_many_into", "pack_bytes_into",
           "unpack_many_from", "chunked_read"]
