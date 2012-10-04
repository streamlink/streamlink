#!/usr/bin/env python

import struct

from .compat import *
from .util import *


class ScriptData:
    NUMBER, BOOLEAN, STRING, OBJECT, RESERVED, NULL, \
    UNDEFINED, REFERENCE, ECMAARRAY, OBJECTEND, STRICTARRAY, \
    DATE, LONGSTRING = range(13)

    class Object(OrderedDict):
        pass

    class ECMAArray(OrderedDict):
        pass

    class ObjectEnd(IOError):
        pass

    class Date(object):
        def __init__(self, timestamp, offset):
            self.timestamp = timestamp
            self.offset = offset

class Packet(object):
    @classmethod
    def _deserialize(cls):
        raise NotImplementedError

    @classmethod
    def deserialize(cls, fd=None, io=None):
        if not io:
            if not fd:
                raise IOError("Missing fd parameter")

            io = PacketIO(fd)

        return cls._deserialize(io)

    def _serialize(self):
        raise NotImplementedError

    def serialize(self, packet=None):
        if not packet:
            packet = PacketIO()

        self._serialize(packet)

        return packet.getvalue()

    def __bytes__(self):
        return self.serialize()

#    __str__ = __bytes__


class PacketIO(object):
    def __init__(self, fd=None):
        if fd:
            self.fd = fd
        else:
            self.io = BytesIO()

        self.data_left = None
        self._objects = []

    def getvalue(self):
        return self.io.getvalue()

    def read(self, size=None):
        if self.data_left is not None:
            if size is None:
                size = self.data_left

            if size > self.data_left:
                raise IOError

            self.data_left -= size

        return self.fd.read(size)

    @property
    def written(self):
        return len(self.getvalue())

    def write(self, data):
        return self.io.write(data)


    # Primitives

    def write_u8(self, num):
        return self.write(struct.pack("B", int(num)))

    def write_u16(self, num):
        return self.write(struct.pack(">H", int(num)))

    def write_s16(self, num):
        return self.write(struct.pack(">h", int(num)))

    def write_u24(self, num):
        ret = struct.pack(">I", int(num))
        return self.write(ret[1:])

    def write_s24(self, num):
        ret = struct.pack(">i", int(num))
        return self.write(ret[1:])

    def write_s32(self, num):
        return self.write(struct.pack(">i", int(num)))

    def write_u32(self, num):
        return self.write(struct.pack(">I", int(num)))

    def write_s32e(self, num):
        ret = struct.pack(">i", int(num))
        return self.write(ret[1:] + byte(ret[0]))

    def write_u64(self, num):
        return self.write(struct.pack(">Q", int(num)))

    def write_s8_8(self, num):
        num = float(num) * float(2**8)
        return self.write_s16(int(num))

    def write_s16_16(self, num):
        num = float(num) * float(2**16)
        return self.write_s32(int(num))

    def write_u3264(self, version, num):
        if version == 1:
            self.write_u64(num)
        else:
            self.write_u32(num)

    def write_double(self, num):
        return self.write(struct.pack(">d", num))

    def write_string(self, string):
        string = bytes(string, "utf8")
        return self.write(string + b"\x00")

    def write_padded(self, value, length, padding=b" "):
        for i in range(length):
            try:
                v = value[i]
                self.write(bytes(v, "ascii"))
            except IndexError:
                self.write(padding)

    def read_u8(self):
        try:
            ret = struct.unpack("B", self.read(1))[0]
        except struct.error:
            raise IOError

        return ret

    def read_u16(self):
        try:
            ret = struct.unpack(">H", self.read(2))[0]
        except struct.error:
            raise IOError

        return ret

    def read_s16(self):
        try:
            ret = struct.unpack(">h", self.read(2))[0]
        except struct.error:
            raise IOError

        return ret

    def read_s8_8(self):
        return float(self.read_s16()) / float(2**8)

    def read_s16_16(self):
        return float(self.read_s32()) / float(2**16)

    def read_s24(self):
        try:
            high, low = struct.unpack(">Bh", self.read(3))
        except struct.error:
            raise IOError

        ret = (high << 16) + low

        return ret

    def read_u24(self):
        try:
            high, low = struct.unpack(">BH", self.read(3))
        except struct.error:
            raise IOError

        ret = (high << 16) + low

        return ret

    def read_s32(self):
        try:
            ret = struct.unpack(">i", self.read(4))[0]
        except struct.error:
            raise IOError

        return ret

    def read_u32(self):
        try:
            ret = struct.unpack(">I", self.read(4))[0]
        except struct.error:
            raise IOError

        return ret

    def read_s32e(self):
        low_high = self.read(4)

        if len(low_high) > 4:
            raise IOError

        combined = byte(low_high[3]) + low_high[:3]

        try:
            ret = struct.unpack(">i", combined)[0]
        except struct.error:
            raise IOError

        return ret

    def read_u3264(self, version):
        if version == 1:
            return self.read_u64()
        else:
            return self.read_u32()

    def read_u64(self):
        try:
            ret = struct.unpack(">Q", self.read(8))[0]
        except struct.error:
            raise IOError

        return ret

    def read_double(self):
        try:
            ret = struct.unpack(">d", self.read(8))[0]
        except struct.error:
            raise IOError

        return ret

    def read_string(self):
        ret = b""

        while True:
            try:
                ch = self.read(1)
            except IOError:
                break

            if ord(ch) == 0:
                break

            ret += ch

        return str(ret, "utf8")

    def read_padded(self, length):
        return str(self.read(length), "ascii").rstrip()

    # ScriptData values

    def read_script_value(self):
        typ = self.read_u8()

        if typ == ScriptData.NUMBER:
            return self.read_script_number()

        elif typ == ScriptData.BOOLEAN:
            return self.read_script_boolean()

        elif typ == ScriptData.STRING:
            return self.read_script_string()

        elif typ == ScriptData.OBJECT:
            return self.read_script_object(ScriptData.Object())

        elif typ == ScriptData.NULL or typ == ScriptData.UNDEFINED:
            return None

        elif typ == ScriptData.REFERENCE:
            ref = self.read_u16()

            return self._objects[ref]

        elif typ == ScriptData.ECMAARRAY:
            container = ScriptData.ECMAArray()
            container.length = self.read_u32()

            return self.read_script_object(container)

        elif typ == ScriptData.OBJECTEND:
            raise ScriptData.ObjectEnd

        elif typ == ScriptData.STRICTARRAY:
            length = self.read_u32()
            rval = []

            for i in range(length):
                val = self.read_script_value()
                rval.append(val)

            return rval

        elif typ == ScriptData.DATE:
            date = self.read_double()
            offset = self.read_s16()

            return ScriptData.Date(date, offset)

        elif typ == ScriptData.LONGSTRING:
            return self.read_script_string(True)

        raise IOError("Unhandled script data type: %d" % typ)

    def read_script_number(self):
        return self.read_double()

    def read_script_boolean(self):
        val = self.read_u8()

        return bool(val)

    def read_script_string(self, full=False):
        if full:
            length = self.read_u32()
        else:
            length = self.read_u16()

        val = self.read(length)

        return str(val, "utf8")

    def read_script_object(self, container):
        while True:
            try:
                key = self.read_script_string()
                value = self.read_script_value()
            except IOError:
                break

            if len(key) == 0:
                break

            container[key] = value

        self._objects.append(container)

        return container

    def write_script_value(self, val):
        if isinstance(val, bool):
            self.write_u8(ScriptData.BOOLEAN)
            self.write_script_boolean(val)

        elif isinstance(val, int) or isinstance(val, float):
            self.write_u8(ScriptData.NUMBER)
            self.write_script_number(val)

        elif isstring(val):
            if len(val) > 65535:
                self.write_u8(ScriptData.LONGSTRING)
            else:
                self.write_u8(ScriptData.STRING)

            self.write_script_string(val)

        elif isinstance(val, list):
            self.write_u8(ScriptData.STRICTARRAY)
            self.write_u32(len(val))

            for value in val:
                self.write_script_value(value)

        elif isinstance(val, ScriptData.Object):
            self.write_u8(ScriptData.OBJECT)
            self.write_script_object(val)

        elif isinstance(val, ScriptData.ECMAArray):
            self.write_u8(ScriptData.ECMAARRAY)
            self.write_u32(len(val))
            self.write_script_object(val)

        elif isinstance(val, ScriptData.Date):
            self.write_u8(ScriptData.DATE)
            self.write_double(val.timestamp)
            self.write_s16(val.offset)

        else:
            raise IOError("Cannot convert {0} to ScriptData value").format(type(val).__name__)


    def write_script_number(self, val):
        self.write_double(float(val))

    def write_script_boolean(self, val):
        self.write_u8(int(val))

    def write_script_string(self, val):
        length = len(val)

        if length > 65535:
            self.write_u32(length)
        else:
            self.write_u16(length)

        self.write(bytes(val, "utf8"))

    def write_script_object(self, val):
        for key, value in val.items():
            self.write_script_string(key)
            self.write_script_value(value)

        # Empty string + marker ends object
        self.write_script_string("")
        self.write_u8(ScriptData.OBJECTEND)

    @classmethod
    def script_value_size(cls, val):
        size = 1

        if isinstance(val, bool):
            size += 1
        elif isinstance(val, int) or isinstance(val, float):
            size += 8
        elif isstring(val):
            size += cls.script_string_size(val)

        elif isinstance(val, list):
            size += 4

            for value in val:
                size += cls.script_value_size(value)

        elif isinstance(val, ScriptData.Object):
            size += cls.script_object_size(val)

        elif isinstance(val, ScriptData.ECMAArray):
            size += 4
            size += cls.script_object_size(val)

        elif isinstance(val, ScriptData.Date):
            size += 10

        return size

    @classmethod
    def script_string_size(cls, val):
        size = len(val)

        if size > 65535:
            size += 4
        else:
            size += 2

        return size

    @classmethod
    def script_object_size(cls, val):
        size = 3

        for key, value in val.items():
            size += cls.script_string_size(key)
            size += cls.script_value_size(value)

        return size


class TagData(Packet):
    @property
    def size(self):
        if isinstance(self.data, Packet):
            return self.data.size
        else:
            return len(self.data)


__all__ = ["Packet", "PacketIO", "TagData", "ScriptData"]
