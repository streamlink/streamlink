from .compat import *
from .util import isstring, pack_bytes_into

from collections import namedtuple
from struct import Struct, error as struct_error

(SCRIPT_DATA_TYPE_NUMBER, SCRIPT_DATA_TYPE_BOOLEAN,
 SCRIPT_DATA_TYPE_STRING, SCRIPT_DATA_TYPE_OBJECT,
 SCRIPT_DATA_TYPE_RESERVED, SCRIPT_DATA_TYPE_NULL,
 SCRIPT_DATA_TYPE_UNDEFINED, SCRIPT_DATA_TYPE_REFERENCE,
 SCRIPT_DATA_TYPE_ECMAARRAY, SCRIPT_DATA_TYPE_OBJECTEND,
 SCRIPT_DATA_TYPE_STRICTARRAY, SCRIPT_DATA_TYPE_DATE,
 SCRIPT_DATA_TYPE_LONGSTRING) = range(13)

class PrimitiveType(Struct):
    def __call__(self, *args):
        return self.pack(*args)

    def read(self, fd):
        data = fd.read(self.size)

        if len(data) != self.size:
            raise IOError("Unable to read required amount of data")

        return self.unpack(data)[0]

class PrimitiveClassType(PrimitiveType):
    def __init__(self, format, cls):
        self.cls = cls

        PrimitiveType.__init__(self, format)

    def pack(self, val):
        return PrimitiveType.pack(self, *val)

    def pack_into(self, buf, offset, val):
        return PrimitiveType.pack_into(self, buf, offset, *val)

    def unpack(self, data):
        vals = PrimitiveType.unpack(self, data)
        rval = self.cls(*vals)

        return (rval,)

    def unpack_from(self, buf, offset):
        vals = PrimitiveType.unpack_from(self, buf, offset)
        rval = self.cls(*vals)

        return (rval,)


class DynamicType(object):
    def __new__(cls, *args, **kwargs):
        return cls.pack(*args, **kwargs)

    @classmethod
    def size(cls, val):
        raise NotImplementedError

    @classmethod
    def pack(cls, val):
        raise NotImplementedError

    @classmethod
    def pack_into(cls, buf, offset, val):
        raise NotImplementedError

    @classmethod
    def read(cls, fd):
        raise NotImplementedError

    @classmethod
    def unpack_from(cls, buf, offset):
        raise NotImplementedError

    @classmethod
    def unpack(cls, buf):
        return cls.unpack_from(buf, 0)


class TwosComplement(PrimitiveType):
    def __init__(self, primitive):
        self.primitive = primitive

        bits = self.primitive.size * 8

        self.maxval = 1 << bits
        self.midval = self.maxval >> 1

        self.upper = self.midval - 1
        self.lower = -self.midval

    @property
    def size(self):
        return 3

    def pack(self, val):
        if val < self.lower or val > self.upper:
            msg = "{0} format requires {1} <= number <= {2}".format(self.primitive.format,
                                                                    self.lower, self.upper)
            raise struct_error(msg)

        if val < 0:
            val = val + self.maxval

        return self.primitive.pack(val)

    def pack_into(self, buf, offset, val):
        if val < self.lower or val > self.upper:
            msg = "{0} format requires {1} <= number <= {2}".format(self.primitive.format,
                                                                    self.lower, self.upper)
            raise struct_error(msg)

        if val < 0:
            val = val + self.maxval

        return self.primitive.pack_into(buf, offset, val)

    def unpack(self, data):
        val = self.primitive.unpack(data)[0]

        if val & self.midval:
            val = val - self.maxval

        return (val,)

    def unpack_from(self, buf, offset):
        val = self.primitive.unpack_from(buf, offset)[0]

        if val & self.midval:
            val = val - self.maxval

        return (val,)


class HighLowCombo(PrimitiveType):
    def __init__(self, format, highbits, reverse=True):
        PrimitiveType.__init__(self, format)

        self.highbits = highbits
        self.lowmask = (1 << highbits) - 1
        self.reverse = reverse
        self.lower = 0
        self.upper = (1 << (self.size * 8)) - 1

    def pack(self, val):
        if val < self.lower or val > self.upper:
            msg = "{0} format requires {1} <= number <= {2}".format(self.format,
                                                                    self.lower, self.upper)
            raise struct_error(msg)

        if self.reverse:
            high = val >> self.highbits
            low = val & self.lowmask
        else:
            high = val & self.lowmask
            low = val >> self.highbits

        return PrimitiveType.pack(self, high, low)

    def pack_into(self, buf, offset, val):
        if val < self.lower or val > self.upper:
            msg = "{0} format requires {1} <= number <= {2}".format(self.format,
                                                                    self.lower, self.upper)
            raise struct_error(msg)

        if self.reverse:
            high = val >> self.highbits
            low = val & self.lowmask
        else:
            high = val & self.lowmask
            low = val >> self.highbits

        return PrimitiveType.pack_into(self, buf, offset, high, low)

    def unpack(self, data):
        high, low = PrimitiveType.unpack(self, data)

        if self.reverse:
            ret = high << self.highbits
            ret |= low
        else:
            ret = high
            ret |= low << self.highbits

        return (ret,)

    def unpack_from(self, buf, offset):
        high, low = PrimitiveType.unpack_from(self, buf, offset)

        if self.reverse:
            ret = high << self.highbits
            ret |= low
        else:
            ret = high
            ret |= low << self.highbits

        return (ret,)



class FixedPoint(PrimitiveType):
    def __init__(self, format, bits):
        self.divider = float(1 << bits)

        PrimitiveType.__init__(self, format)

    def pack(self, val):
        val *= self.divider

        return PrimitiveType.pack(self, int(val))

    def pack_into(self, buf, offset, val):
        val *= self.divider

        return PrimitiveType.pack_into(self, buf, offset, int(val))

    def unpack(self, data):
        val = PrimitiveType.unpack(self, data)[0]
        val /= self.divider

        return (val,)

    def unpack(self, buf, offset):
        val = PrimitiveType.unpack_from(self, buf, offset)[0]
        val /= self.divider

        return (val,)

class PaddedBytes(PrimitiveType):
    def __init__(self, size, padding):
        self.padded_size = size
        self.padding = bytes(padding, "ascii")

    @property
    def size(self):
        return self.padded_size

    def pack(self, val):
        rval = bytes(val[:self.size], "ascii")

        if len(rval) < self.size:
            paddinglen = self.size - len(rval)
            rval += self.padding * paddinglen

        return rval

    def pack_into(self, buf, offset, val):
        offset = pack_bytes_into(buf, offset,
                                 bytes(val[:self.size], "ascii"))

        if len(rval) < self.size:
            paddinglen = self.size - len(rval)
            offset = pack_bytes_into(buf, offset, self.padding * paddinglen)

    def unpack(self, data):
        return (str(data.rstrip(self.padding), "ascii"),)

    def unpack_from(self, buf, offset):
        data = buf[offset:offset + self.padded_size]
        return (str(data.rstrip(self.padding), "ascii"),)

""" 8-bit integer """

U8 = PrimitiveType("B")
S8 = PrimitiveType("b")


""" 16-bit integer """

U16BE = PrimitiveType(">H")
S16BE = PrimitiveType(">h")
U16LE = PrimitiveType("<H")
S16LE = PrimitiveType("<h")


""" 24-bit integer """

U24BE = HighLowCombo(">HB", 8, True)
S24BE = TwosComplement(U24BE)
U24LE = HighLowCombo("<HB", 16, False)
S24LE = TwosComplement(U24LE)


""" 32-bit integer """

U32BE = PrimitiveType(">I")
S32BE = PrimitiveType(">i")
U32LE = PrimitiveType("<I")
S32LE = PrimitiveType("<i")


""" 64-bit integer """

U64BE = PrimitiveType(">Q")
U64LE = PrimitiveType("<Q")


""" Fixed point numbers """

U8_8BE = FixedPoint(">H", 8)
S8_8BE = FixedPoint(">h", 8)
U16_16BE = FixedPoint("<I", 16)
S16_16BE = FixedPoint("<i", 16)

U8_8LE = FixedPoint("<H", 8)
S8_8LE = FixedPoint("<h", 8)
U16_16LE = FixedPoint("<I", 16)
S16_16LE = FixedPoint("<i", 16)

DoubleLE = PrimitiveType("<d")
DoubleBE = PrimitiveType(">d")


""" Various types """

FourCC = PaddedBytes(4, " ")


""" Script data types """

ScriptDataNumber = DoubleBE
ScriptDataBoolean = PrimitiveType("?")

class U3264(DynamicType):
    @classmethod
    def size(cls, val, version):
        if version == 1:
            return U64BE.size
        else:
            return U32BE.size

    @classmethod
    def pack(cls, val, version):
        if version == 1:
            return U64BE(val)
        else:
            return U32BE(val)

    @classmethod
    def pack_into(cls, buf, offset, val, version):
        if version == 1:
            prim = U64BE
        else:
            prim = U32BE

        prim.pack_into(buf, offset, val)

        return offset + prim.size

    @classmethod
    def read(cls, fd, version):
        if version == 1:
            return U64BE.read(fd)
        else:
            return U32BE.read(fd)

    @classmethod
    def unpack_from(cls, buf, offset):
        if version == 1:
            prim = U64BE
        else:
            prim = U32BE

        rval = prim.unpack_from(buf, offset)
        offset += prim.size

        return (rval, offset)


class String(DynamicType):
    @classmethod
    def size(cls, *args, **kwargs):
        return len(cls.pack(*args, **kwargs))

    @classmethod
    def pack(cls, val, encoding="utf8", errors="ignore"):
        rval = val.encode(encoding, errors)

        return rval

    @classmethod
    def pack_into(cls, buf, offset, val,
                  encoding="utf8", errors="ignore"):

        return pack_bytes_into(buf, offset,
                               val.encode(encoding, errors))

class CString(String):
    EndMarker = b"\x00"

    @classmethod
    def pack(cls, *args, **kwargs):
        rval = String.pack(*args, **kwargs)
        rval += CString.EndMarker

        return rval

    @classmethod
    def pack_into(cls, buf, offset, *args, **kwargs):
        offset = String.pack_into(buf, offset, *args, **kwargs)
        U8.pack_into(buf, offset, 0)

        return offset + 1

    @classmethod
    def read(cls, fd, encoding="utf8", errors="ignore"):
        rval = b""

        while True:
            ch = fd.read(1)

            if len(ch) == 0 or ch == CString.EndMarker:
                break

            rval += ch

        return rval.decode(encoding, errors)

    @classmethod
    def unpack_from(cls, buf, offset, encoding="utf8", errors="ignore"):
        end = buf[offset:].find(b"\x00")
        rval = buf[offset:offset + end].decode(encoding, errors)
        offset += end + 1

        return (rval, offset)


class ScriptDataType(object):
    __identifier__ = 0

class ScriptDataString(String):
    __size_primitive__ = U16BE

    @classmethod
    def pack(cls, val, *args, **kwargs):
        rval = String.pack(val, *args, **kwargs)
        size = cls.__size_primitive__(len(rval))

        return size + rval

    @classmethod
    def pack_into(cls, buf, offset, val, *args, **kwargs):
        noffset = String.pack_into(buf, offset + cls.__size_primitive__.size,
                                   val, *args, **kwargs)

        cls.__size_primitive__.pack_into(buf, offset,
                                         (noffset - offset) - cls.__size_primitive__.size)

        return noffset

    @classmethod
    def read(cls, fd, encoding="utf8", errors="ignore"):
        size = cls.__size_primitive__.read(fd)
        data = fd.read(size)

        return data.decode(encoding, errors)

    @classmethod
    def unpack_from(cls, buf, offset, encoding="utf8", errors="ignore"):
        size = cls.__size_primitive__.unpack_from(buf, offset)[0]
        offset += cls.__size_primitive__.size

        data = buf[offset:offset + size].decode(encoding, errors)
        offset += size

        return (data, offset)

class ScriptDataLongString(ScriptDataString):
    __size_primitive__ = U32BE


class ScriptDataObjectEnd(Exception):
    pass

class ScriptDataObject(OrderedDict, ScriptDataType):
    __identifier__ = SCRIPT_DATA_TYPE_OBJECT

    @classmethod
    def size(cls, val):
        size = 3

        for key, value in val.items():
            size += ScriptDataString.size(key)
            size += ScriptDataValue.size(value)

        return size

    @classmethod
    def pack(cls, val):
        rval = b""

        for key, value in val.items():
            rval += ScriptDataString(key)
            rval += ScriptDataValue.pack(value)

        # Zero length key + object end identifier ends object
        rval += ScriptDataString("")
        rval += U8(SCRIPT_DATA_TYPE_OBJECTEND)

        return rval

    @classmethod
    def pack_into(cls, buf, offset, val):
        for key, value in val.items():
            offset = ScriptDataString.pack_into(buf, offset, key)
            offset = ScriptDataValue.pack_into(buf, offset, value)

        # Zero length key + object end identifier ends object
        offset = ScriptDataString.pack_into(buf, offset, "")
        U8.pack_into(buf, offset, SCRIPT_DATA_TYPE_OBJECTEND)

        return offset + U8.size

    @classmethod
    def read(cls, fd):
        rval = cls()

        while True:
            try:
                key = ScriptDataString.read(fd)
                value = ScriptDataValue.read(fd)
            except ScriptDataObjectEnd:
                break

            if len(key) == 0:
                break

            rval[key] = value

        return rval

    @classmethod
    def unpack_from(cls, buf, offset):
        rval = cls()

        while True:
            try:
                key, offset = ScriptDataString.unpack_from(buf, offset)
                value, offset = ScriptDataValue.unpack_from(buf, offset)
            except ScriptDataObjectEnd:
                offset += 1
                break

            if len(key) == 0:
                break

            rval[key] = value

        return (rval, offset)


class ScriptDataECMAArray(ScriptDataObject):
    __identifier__ = SCRIPT_DATA_TYPE_ECMAARRAY

    @classmethod
    def size(cls, val):
        return 4 + ScriptDataObject.size(val)

    @classmethod
    def pack(cls, val):
        rval = U32BE(len(val))
        rval += ScriptDataObject.pack(val)

        return rval

    @classmethod
    def pack_into(cls, buf, offset, val):
        U32BE.pack_into(buf, offset, len(val))

        return ScriptDataObject.pack_into(buf, offset + U32BE.size,
                                          val)

    @classmethod
    def read(cls, fd):
        length = U32BE.read(fd)
        val = ScriptDataObject.read(fd)

        return cls(val)

    @classmethod
    def unpack_from(cls, buf, offset):
        length = U32BE.unpack_from(buf, offset)
        offset += U32BE.size

        val, offset = ScriptDataObject.unpack_from(buf, offset)

        return (cls(val), offset)

class ScriptDataStrictArray(DynamicType):
    @classmethod
    def size(cls, val):
        size = 4

        for sdval in val:
            size += ScriptDataValue.size(sdval)

        return size

    @classmethod
    def pack(cls, val):
        rval = U32BE(len(val))

        for sdval in val:
            rval += ScriptDataValue.pack(sdval)

        return rval

    @classmethod
    def pack_into(cls, buf, offset, val):
        U32BE.pack_into(buf, offset, len(val))
        offset += U32BE.size

        for sdval in val:
            offset = ScriptDataValue.pack_into(buf, offset, sdval)

        return offset

    @classmethod
    def read(cls, fd):
        length = U32BE.read(fd)
        rval = []

        for i in range(length):
            val = ScriptDataValue.read(fd)
            rval.append(val)

        return rval

    @classmethod
    def unpack_from(cls, buf, offset):
        length = U32BE.unpack_from(buf, offset)[0]
        offset += U32BE.size
        rval = []

        for i in range(length):
            val, offset = ScriptDataValue.unpack_from(buf, offset)
            rval.append(val)

        return (rval, offset)


ScriptDataDate = namedtuple("ScriptDataDate", ["timestamp", "offset"])
ScriptDataDateStruct = PrimitiveClassType(">dh", ScriptDataDate)
ScriptDataDate.__identifier__ = SCRIPT_DATA_TYPE_DATE
ScriptDataDate.__packer__ = ScriptDataDateStruct

ScriptDataReference = namedtuple("ScriptDataReference", ["reference"])
ScriptDataReferenceStruct = PrimitiveClassType(">H", ScriptDataReference)
ScriptDataReference.__identifier__ = SCRIPT_DATA_TYPE_REFERENCE
ScriptDataReference.__packer__ = ScriptDataReferenceStruct


class ScriptDataValue(DynamicType, ScriptDataType):
    # key: identifier, value: unpacker class
    PrimitiveReaders = {
        SCRIPT_DATA_TYPE_NUMBER: ScriptDataNumber,
        SCRIPT_DATA_TYPE_BOOLEAN: ScriptDataBoolean,
        SCRIPT_DATA_TYPE_REFERENCE: ScriptDataReferenceStruct,
        SCRIPT_DATA_TYPE_DATE: ScriptDataDateStruct,
    }

    DynamicReaders = {
        SCRIPT_DATA_TYPE_STRING: ScriptDataString,
        SCRIPT_DATA_TYPE_LONGSTRING: ScriptDataLongString,
        SCRIPT_DATA_TYPE_OBJECT: ScriptDataObject,
        SCRIPT_DATA_TYPE_ECMAARRAY: ScriptDataECMAArray,
        SCRIPT_DATA_TYPE_STRICTARRAY: ScriptDataStrictArray,
    }

    Readers = PrimitiveReaders.copy()
    Readers.update(DynamicReaders)

    @classmethod
    def size(cls, val):
        size = 1

        if isinstance(val, bool):
            size += ScriptDataBoolean.size

        elif isinstance(val, (int, float)):
            size += ScriptDataNumber.size

        elif isinstance(val, list):
            size += ScriptDataStrictArray.size(val)

        elif isstring(val):
            if len(val) > 0xFFFF:
                size += ScriptDataLongString.size(val)
            else:
                size += ScriptDataString.size(val)

        elif isinstance(val, ScriptDataType):
            cls = type(val)
            size += cls.size(val)

        elif type(val) in (ScriptDataDate, ScriptDataReference):
            cls = type(val)
            packer = cls.__packer__
            size += packer.size

        return size

    @classmethod
    def pack(cls, val):
        rval = b""

        if isinstance(val, bool):
            rval += U8(SCRIPT_DATA_TYPE_BOOLEAN)
            rval += ScriptDataBoolean(val)

        elif isinstance(val, (int, float)):
            rval += U8(SCRIPT_DATA_TYPE_NUMBER)
            rval += ScriptDataNumber(val)

        elif isinstance(val, list):
            rval += U8(SCRIPT_DATA_TYPE_STRICTARRAY)
            rval += ScriptDataStrictArray(val)

        elif isstring(val):
            if len(val) > 0xFFFF:
                rval += U8(SCRIPT_DATA_TYPE_LONGSTRING)
                rval += ScriptDataLongString(val)
            else:
                rval += U8(SCRIPT_DATA_TYPE_STRING)
                rval += ScriptDataString(val)

        elif val is None:
            rval += U8(SCRIPT_DATA_TYPE_NULL)

        elif isinstance(val, ScriptDataType):
            cls = type(val)
            rval += U8(cls.__identifier__)
            rval += cls.pack(val)

        elif type(val) in (ScriptDataDate, ScriptDataReference):
            cls = type(val)
            packer = cls.__packer__

            rval += U8(cls.__identifier__)
            rval += packer.pack(val)

        else:
            raise ValueError("Unable to pack value of type {0}".format(type(val)))

        return rval

    @classmethod
    def pack_into(cls, buf, offset, val):
        if isinstance(val, bool):
            U8.pack_into(buf, offset, SCRIPT_DATA_TYPE_BOOLEAN)
            offset += U8.size

            ScriptDataBoolean.pack_into(buf, offset, val)
            offset += ScriptDataBoolean.size

        elif isinstance(val, (int, float)):
            U8.pack_into(buf, offset, SCRIPT_DATA_TYPE_NUMBER)
            offset += U8.size

            ScriptDataNumber.pack_into(buf, offset, val)
            offset += ScriptDataNumber.size

        elif isinstance(val, list):
            U8.pack_into(buf, offset, SCRIPT_DATA_TYPE_STRICTARRAY)
            offset += U8.size
            offset = ScriptDataStrictArray.pack_into(buf, offset, val)

        elif isstring(val):
            if len(val) > 0xFFFF:
                U8.pack_into(buf, offset, SCRIPT_DATA_TYPE_LONGSTRING)
                offset += U8.size
                offset = ScriptDataLongString.pack_into(buf, offset, val)
            else:
                U8.pack_into(buf, offset, SCRIPT_DATA_TYPE_STRING)
                offset += U8.size
                offset = ScriptDataString.pack_into(buf, offset, val)

        elif val is None:
            U8.pack_into(buf, offset, SCRIPT_DATA_TYPE_NULL)

        elif isinstance(val, ScriptDataType):
            cls = type(val)
            U8.pack_into(buf, offset, cls.__identifier__)
            offset += U8.size
            offset = cls.pack_into(buf, offset, val)

        elif type(val) in (ScriptDataDate, ScriptDataReference):
            cls = type(val)
            packer = cls.__packer__

            U8.pack_into(buf, offset, cls.__identifier__)
            offset += U8.size

            packer.pack_into(buf, offset, val)
            offset += packer.size

        else:
            raise ValueError("Unable to pack value of type {0}".format(type(val)))

        return offset

    @classmethod
    def read(cls, fd):
        type_ = U8.read(fd)

        if type_ in ScriptDataValue.Readers:
            return ScriptDataValue.Readers[type_].read(fd)

        elif type_ == SCRIPT_DATA_TYPE_OBJECTEND:
            raise ScriptDataObjectEnd

        elif (type_ == SCRIPT_DATA_TYPE_NULL or
              type_ == SCRIPT_DATA_TYPE_UNDEFINED):

            return None

        else:
            raise IOError("Unhandled script data type: {0}".format(type_))

    @classmethod
    def unpack_from(cls, buf, offset):
        type_ = U8.unpack_from(buf, offset)[0]
        offset += U8.size

        if type_ in ScriptDataValue.DynamicReaders:
            return ScriptDataValue.Readers[type_].unpack_from(buf, offset)

        elif type_ in ScriptDataValue.PrimitiveReaders:
            reader = ScriptDataValue.PrimitiveReaders[type_]
            rval = reader.unpack_from(buf, offset)[0]
            offset += reader.size

            return (rval, offset)

        elif type_ == SCRIPT_DATA_TYPE_OBJECTEND:
            raise ScriptDataObjectEnd

        elif (type_ == SCRIPT_DATA_TYPE_NULL or
              type_ == SCRIPT_DATA_TYPE_UNDEFINED):

            return (None, offset)

        else:
            raise IOError("Unhandled script data type: {0}".format(type_))



