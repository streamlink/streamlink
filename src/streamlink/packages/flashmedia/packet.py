import struct


class Packet(object):
    exception = IOError

    @classmethod
    def _deserialize(cls, fd):
        raise NotImplementedError

    @classmethod
    def _deserialize_from(cls, buf, offset, **kw):
        raise NotImplementedError

    @classmethod
    def deserialize(cls, fd, **kw):
        try:
            return cls._deserialize(fd, **kw)
        except (struct.error, IOError) as err:
            raise cls.exception(err)

    @classmethod
    def deserialize_from(cls, buf, offset, **kw):
        try:
            return cls._deserialize_from(buf, offset, **kw)
        except (struct.error, IOError) as err:
            raise cls.exception(err)

    def _serialize(self):
        raise NotImplementedError

    def _serialize_into(self, buf, offset):
        raise NotImplementedError

    def serialize(self, packet=None, **kw):
        if packet is None:
            packet = bytearray()

        self._serialize(packet, **kw)

        return packet

    def serialize2(self):
        buf = bytearray(self.size)
        self.serialize_into(buf, 0)
        return buf

    def serialize_into(self, buf, offset):
        return self._serialize_into(buf, offset)

    def __bytes__(self):
        return self.serialize()


class TagData(Packet):
    @property
    def size(self):
        if isinstance(self.data, Packet):
            return self.data.size
        else:
            return len(self.data)


__all__ = ["Packet", "TagData"]
