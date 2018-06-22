from .compat import OrderedDict, is_py2, str, bytes, integer_types, string_types
from .util import pack_bytes_into

from collections import namedtuple
from struct import Struct, error as struct_error
import inspect


getargspec = getattr(inspect, "getfullargspec", inspect.getargspec)

(SCRIPT_DATA_TYPE_NUMBER, SCRIPT_DATA_TYPE_BOOLEAN,
 SCRIPT_DATA_TYPE_STRING, SCRIPT_DATA_TYPE_OBJECT,
 SCRIPT_DATA_TYPE_RESERVED, SCRIPT_DATA_TYPE_NULL,
 SCRIPT_DATA_TYPE_UNDEFINED, SCRIPT_DATA_TYPE_REFERENCE,
 SCRIPT_DATA_TYPE_ECMAARRAY, SCRIPT_DATA_TYPE_OBJECTEND,
 SCRIPT_DATA_TYPE_STRICTARRAY, SCRIPT_DATA_TYPE_DATE,
 SCRIPT_DATA_TYPE_LONGSTRING) = range(13)

SCRIPT_DATA_TYPE_AMF3 = 0x11

(AMF3_TYPE_UNDEFINED, AMF3_TYPE_NULL, AMF3_TYPE_FALSE, AMF3_TYPE_TRUE,
 AMF3_TYPE_INTEGER, AMF3_TYPE_DOUBLE, AMF3_TYPE_STRING, AMF3_TYPE_XML_DOC,
 AMF3_TYPE_DATE, AMF3_TYPE_ARRAY, AMF3_TYPE_OBJECT, AMF3_TYPE_XML,
 AMF3_TYPE_BYTE_ARRAY, AMF3_TYPE_VECTOR_INT, AMF3_TYPE_VECTOR_UINT,
 AMF3_TYPE_VECTOR_DOUBLE, AMF3_TYPE_VECTOR_OBJECT, AMF3_TYPE_DICT) = range(0x12)

AMF3_EMPTY_STRING = 0x01
AMF3_DYNAMIC_OBJECT = 0x0b
AMF3_CLOSE_DYNAMIC_OBJECT = 0x01
AMF3_CLOSE_DYNAMIC_ARRAY = 0x01
AMF3_MIN_INTEGER = -268435456
AMF3_MAX_INTEGER = 268435455


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

    def unpack_from(self, buf, offset):
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
        rval = bytes(val[:self.size], "ascii")
        offset = pack_bytes_into(buf, offset, rval)

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
    def unpack_from(cls, buf, offset, version):
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
        U32BE.read(fd)  # Length
        val = ScriptDataObject.read(fd)

        return cls(val)

    @classmethod
    def unpack_from(cls, buf, offset):
        U32BE.unpack_from(buf, offset)  # Length
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

        elif isinstance(val, string_types):
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

        elif isinstance(val, AMF3ObjectBase):
            size += U8.size
            size += AMF3Value.size(val)

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

        elif isinstance(val, string_types):
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

        elif isinstance(val, AMF3ObjectBase):
            rval += U8(SCRIPT_DATA_TYPE_AMF3)
            rval += AMF3Value.pack(val)

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

        elif isinstance(val, string_types):
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
    def read(cls, fd, marker=None):
        if marker is None:
            type_ = U8.read(fd)
        else:
            type_ = marker

        if type_ == SCRIPT_DATA_TYPE_AMF3:
            return AMF3Value.read(fd)

        elif type_ in ScriptDataValue.Readers:
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
            raise IOError("Unhandled script data type: {0}".format(hex(type_)))


class AMF0Value(ScriptDataValue):
    pass


class AMF0String(ScriptDataString):
    pass


AMF0Number = ScriptDataNumber

AMF3Double = ScriptDataNumber


class AMF3Type(ScriptDataType):
    pass


class AMF3Integer(DynamicType, AMF3Type):
    __identifier__ = AMF3_TYPE_INTEGER

    @classmethod
    def size(cls, val):
        val &= 0x1fffffff

        if val < 0x80:
            return 1
        elif val < 0x4000:
            return 2
        elif val < 0x200000:
            return 3
        elif val < 0x40000000:
            return 4

    @classmethod
    def pack(cls, val):
        size = cls.size(val)
        buf = bytearray(size)
        offset = cls.pack_into(buf, 0, val)

        return bytes(buf[:offset])

    @classmethod
    def pack_into(cls, buf, offset, val):
        val &= 0x1fffffff

        if val < 0x80:
            buf[offset] = val
            offset += 1
        elif val < 0x4000:
            buf[offset] = (val >> 7 & 0x7f) | 0x80
            buf[offset + 1] = val & 0x7f
            offset += 2
        elif val < 0x200000:
            buf[offset] = (val >> 14 & 0x7f) | 0x80
            buf[offset + 1] = (val >> 7 & 0x7f) | 0x80
            buf[offset + 2] = val & 0x7f
            offset += 3
        elif val < 0x40000000:
            buf[offset] = (val >> 22 & 0x7f) | 0x80
            buf[offset + 1] = (val >> 15 & 0x7f) | 0x80
            buf[offset + 2] = (val >> 8 & 0x7f) | 0x80
            buf[offset + 3] = val & 0xff
            offset += 4

        return offset

    @classmethod
    def read(cls, fd):
        rval, byte_count = 0, 0
        byte = U8.read(fd)

        while (byte & 0x80) != 0 and byte_count < 3:
            rval <<= 7
            rval |= byte & 0x7f

            byte = U8.read(fd)
            byte_count += 1

        if byte_count < 3:
            rval <<= 7
            rval |= byte & 0x7F
        else:
            rval <<= 8
            rval |= byte & 0xff

        if (rval & 0x10000000) != 0:
            rval -= 0x20000000

        return rval


class AMF3String(String):
    @classmethod
    def size(cls, val, cache):
        data = String.pack(val, "utf8", "ignore")
        size = len(data)

        if size == 0:
            return U8.size
        elif val in cache:
            index = cache.index(val)
            return AMF3Integer.size(index << 1)
        else:
            cache.append(val)
            return AMF3Integer.size(size << 1 | 1) + size

    @classmethod
    def pack(cls, val, cache):
        data = String.pack(val, "utf8", "ignore")
        size = len(data)

        if size == 0:
            return U8(AMF3_EMPTY_STRING)
        elif val in cache:
            index = cache.index(val)
            return AMF3Integer(index << 1)
        else:
            cache.append(val)

            chunks = []
            chunks.append(AMF3Integer(size << 1 | 1))
            chunks.append(data)

            return b"".join(chunks)

    @classmethod
    def read(cls, fd, cache):
        header = AMF3Integer.read(fd)

        if (header & 1) == 0:
            index = header >> 1

            return cache[index]
        else:
            size = header >> 1
            data = fd.read(size)
            rval = data.decode("utf8", "ignore")

            if len(data) > 0:
                cache.append(rval)

            return rval


class AMF3ObjectBase(object):
    __dynamic__ = False
    __externalizable__ = False
    __members__ = []

    _registry = {}

    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return "<{0} {1!r}".format(self.__class__.__name__, self.__dict__)

    @classmethod
    def register(cls, name):
        def deco(amfcls):
            amfcls.__name__ = name

            if not amfcls.__members__:
                amfcls.__members__ = getargspec(amfcls.__init__).args[1:]

            cls._registry[name] = amfcls

            return amfcls

        return deco

    @classmethod
    def lookup(cls, name):
        return cls._registry.get(name, None)

    @classmethod
    def create(cls, name, externalizable, dynamic, members):
        if is_py2:
            name = name.encode("utf8")

        amfcls = type(name, (cls,), {})
        amfcls.__externalizable__ = externalizable
        amfcls.__members__ = members

        return amfcls


class AMF3Object(OrderedDict, AMF3ObjectBase):
    __dynamic__ = True


class AMF3ObjectPacker(DynamicType, AMF3Type):
    __identifier__ = AMF3_TYPE_OBJECT

    @classmethod
    def size(cls, val, str_cache, object_cache, traits_cache):
        if val in object_cache:
            index = object_cache.index(val)
            return AMF3Integer.size(index << 1)
        else:
            object_cache.append(val)
            size = 0
            traits = type(val)

            if traits in traits_cache:
                index = traits_cache.index(traits)
                size += AMF3Integer.size(index << 2 | 0x01)
            else:
                header = 0x03

                if traits.__dynamic__:
                    header |= 0x02 << 2

                if traits.__externalizable__:
                    header |= 0x01 << 2

                header |= (len(traits.__members__)) << 4
                size += AMF3Integer.size(header)

                if isinstance(val, AMF3Object):
                    size += U8.size
                else:
                    size += AMF3String.size(traits.__name__, cache=str_cache)
                    traits_cache.append(traits)

                for member in traits.__members__:
                    size += AMF3String.size(member, cache=str_cache)

            for member in traits.__members__:
                value = getattr(val, member)
                size += AMF3Value.size(value, str_cache=str_cache,
                                       object_cache=object_cache,
                                       traits_cache=traits_cache)

            if traits.__dynamic__:
                if isinstance(val, AMF3Object):
                    iterator = val.items()
                else:
                    iterator = val.__dict__.items()

                for key, value in iterator:
                    if key in traits.__members__:
                        continue

                    size += AMF3String.size(key, cache=str_cache)
                    size += AMF3Value.size(value, str_cache=str_cache,
                                           object_cache=object_cache,
                                           traits_cache=traits_cache)

                size += U8.size

            return size

    @classmethod
    def pack(cls, val, str_cache, object_cache, traits_cache):
        chunks = []

        if val in object_cache:
            index = object_cache.index(val)
            return AMF3Integer(index << 1)
        else:
            object_cache.append(val)
            chunks = []
            traits = type(val)

            if traits in traits_cache:
                index = traits_cache.index(traits)
                chunks.append(AMF3Integer(index << 2 | 0x01))
            else:
                header = 0x03

                if traits.__dynamic__:
                    header |= 0x02 << 2

                if traits.__externalizable__:
                    header |= 0x01 << 2

                header |= (len(traits.__members__)) << 4
                chunks.append(AMF3Integer(header))

                if isinstance(val, AMF3Object):
                    chunks.append(U8(AMF3_EMPTY_STRING))
                else:
                    chunks.append(AMF3String(traits.__name__, cache=str_cache))
                    traits_cache.append(traits)

                for member in traits.__members__:
                    chunks.append(AMF3String(member, cache=str_cache))

            for member in traits.__members__:
                value = getattr(val, member)
                value = AMF3Value.pack(value, str_cache=str_cache,
                                       object_cache=object_cache,
                                       traits_cache=traits_cache)
                chunks.append(value)

            if traits.__dynamic__:
                if isinstance(val, AMF3Object):
                    iterator = val.items()
                else:
                    iterator = val.__dict__.items()

                for key, value in iterator:
                    if key in traits.__members__:
                        continue

                    key = AMF3String(key, cache=str_cache)
                    value = AMF3Value.pack(value, str_cache=str_cache,
                                           object_cache=object_cache,
                                           traits_cache=traits_cache)

                    chunks.append(key)
                    chunks.append(value)

                # Empty string is end of dynamic values
                chunks.append(U8(AMF3_CLOSE_DYNAMIC_ARRAY))

            return b"".join(chunks)

    @classmethod
    def read(cls, fd, str_cache, object_cache, traits_cache):
        header = AMF3Integer.read(fd)
        obj = None

        if (header & 1) == 0:
            index = header >> 1
            obj = object_cache[index]
        else:
            header >>= 1

            if (header & 1) == 0:
                index = header >> 1
                traits = traits_cache[index]
            else:
                externalizable = (header & 2) != 0
                dynamic = (header & 4) != 0
                members_len = header >> 3
                class_name = AMF3String.read(fd, cache=str_cache)
                members = []

                for i in range(members_len):
                    member_name = AMF3String.read(fd, cache=str_cache)
                    members.append(member_name)

                if len(class_name) == 0:
                    traits = AMF3Object
                elif AMF3ObjectBase.lookup(class_name):
                    traits = AMF3ObjectBase.lookup(class_name)
                    traits.__members__ = members
                    traits.__dynamic__ = dynamic
                    traits_cache.append(traits)
                else:
                    traits = AMF3ObjectBase.create(class_name, externalizable,
                                                   dynamic, members)
                    traits_cache.append(traits)

            values = OrderedDict()

            for member in traits.__members__:
                value = AMF3Value.read(fd, str_cache=str_cache,
                                       object_cache=object_cache,
                                       traits_cache=traits_cache)

                values[member] = value

            if traits.__dynamic__:
                key = AMF3String.read(fd, cache=str_cache)
                while len(key) > 0:
                    value = AMF3Value.read(fd, str_cache=str_cache,
                                           object_cache=object_cache,
                                           traits_cache=traits_cache)
                    values[key] = value
                    key = AMF3String.read(fd, cache=str_cache)

            if traits == AMF3Object:
                obj = traits(values)
            else:
                obj = traits(**values)

        return obj


class AMF3Array(OrderedDict):
    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], list):
            OrderedDict.__init__(self, **kwargs)

            for i, value in enumerate(args[0]):
                self[i] = value
        else:
            OrderedDict.__init__(self, *args, **kwargs)

    def dense_keys(self):
        dense_keys = []

        for i in range(len(self)):
            if i in self:
                dense_keys.append(i)

        return dense_keys

    def dense_values(self):
        for key in self.dense_keys():
            yield self[key]


class AMF3ArrayPacker(DynamicType, AMF3Type):
    __identifier__ = AMF3_TYPE_ARRAY

    @classmethod
    def size(cls, val, str_cache, object_cache, traits_cache):
        if val in object_cache:
            index = object_cache.index(val)
            return AMF3Integer.size(index << 1)
        else:
            object_cache.append(val)
            size = 0

            if isinstance(val, AMF3Array):
                dense_keys = val.dense_keys()
                length = len(dense_keys)
            else:
                length = len(val)
                dense_keys = list(range(length))

            header = length << 1 | 1
            size += AMF3Integer.size(header)

            if isinstance(val, AMF3Array):
                for key, value in val.items():
                    if key in dense_keys:
                        continue

                    size += AMF3String.size(key, cache=str_cache)
                    size += AMF3Value.size(value, str_cache=str_cache,
                                           object_cache=object_cache,
                                           traits_cache=traits_cache)

            size += U8.size

            for key in dense_keys:
                value = val[key]
                size += AMF3Value.size(value, str_cache=str_cache,
                                       object_cache=object_cache,
                                       traits_cache=traits_cache)

            return size

    @classmethod
    def pack(cls, val, str_cache, object_cache, traits_cache):
        if val in object_cache:
            index = object_cache.index(val)
            return AMF3Integer(index << 1)
        else:
            object_cache.append(val)
            chunks = []

            if isinstance(val, AMF3Array):
                dense_keys = val.dense_keys()
                length = len(dense_keys)
            else:
                length = len(val)
                dense_keys = list(range(length))

            header = length << 1 | 1
            chunks.append(AMF3Integer(header))

            if isinstance(val, AMF3Array):
                for key, value in val.items():
                    if key in dense_keys:
                        continue

                    chunks.append(AMF3String(key, cache=str_cache))

                    value = AMF3Value.pack(value, str_cache=str_cache,
                                           object_cache=object_cache,
                                           traits_cache=traits_cache)
                    chunks.append(value)

            # Empty string is end of dynamic values
            chunks.append(U8(AMF3_CLOSE_DYNAMIC_ARRAY))

            for key in dense_keys:
                value = val[key]
                value = AMF3Value.pack(value, str_cache=str_cache,
                                       object_cache=object_cache,
                                       traits_cache=traits_cache)
                chunks.append(value)

            return b"".join(chunks)

    @classmethod
    def read(cls, fd, str_cache, object_cache, traits_cache):
        header = AMF3Integer.read(fd)
        obj = None

        if (header & 1) == 0:
            index = header >> 1
            obj = object_cache[index]
        else:
            header >>= 1
            obj = AMF3Array()
            object_cache.append(obj)

            key = AMF3String.read(fd, cache=str_cache)
            while len(key) > 0:
                value = AMF3Value.read(fd, str_cache=str_cache,
                                       object_cache=object_cache,
                                       traits_cache=traits_cache)
                obj[key] = value
                key = AMF3String.read(fd, cache=str_cache)

            for i in range(header):
                value = AMF3Value.read(fd, str_cache=str_cache,
                                       object_cache=object_cache,
                                       traits_cache=traits_cache)
                obj[i] = value

        return obj


class AMF3Date(object):
    def __init__(self, time):
        self.time = time


class AMF3DatePacker(DynamicType, AMF3Type):
    __identifier__ = AMF3_TYPE_ARRAY

    @classmethod
    def size(cls, val, cache):
        if val in cache:
            index = cache.index(val)
            return AMF3Integer.size(index << 1)
        else:
            cache.append(val)

            return AMF3Double.size + U8.size

    @classmethod
    def pack(cls, val, cache):
        if val in cache:
            index = cache.index(val)
            return AMF3Integer(index << 1)
        else:
            cache.append(val)
            chunks = [U8(AMF3_TYPE_NULL),
                      AMF3Double(val.time)]

            return b"".join(chunks)

    @classmethod
    def read(cls, fd, cache):
        header = AMF3Integer.read(fd)

        if (header & 1) == 0:
            index = header >> 1
            return cache[index]
        else:
            time = AMF3Double.read(fd)
            date = AMF3Date(time)
            cache.append(date)

            return date


class AMF3Value(DynamicType):
    PrimitiveReaders = {
        AMF3_TYPE_DOUBLE: AMF3Double,
    }

    DynamicReaders = {
        AMF3_TYPE_INTEGER: AMF3Integer,
    }

    Readers = PrimitiveReaders.copy()
    Readers.update(DynamicReaders)

    @classmethod
    def size(cls, val, str_cache=None, object_cache=None, traits_cache=None):
        if str_cache is None:
            str_cache = []

        if object_cache is None:
            object_cache = []

        if traits_cache is None:
            traits_cache = []

        size = U8.size

        if isinstance(val, bool) and val in (False, True):
            pass

        elif val is None:
            pass

        elif isinstance(val, integer_types):
            if val < AMF3_MIN_INTEGER or val > AMF3_MAX_INTEGER:
                size += AMF3Double.size
            else:
                size += AMF3Integer.size(val)

        elif isinstance(val, float):
            size += AMF3Double.size

        elif isinstance(val, (AMF3Array, list)):
            size += AMF3ArrayPacker.size(val, str_cache=str_cache,
                                         object_cache=object_cache,
                                         traits_cache=traits_cache)

        elif isinstance(val, string_types):
            size += AMF3String.size(val, cache=str_cache)

        elif isinstance(val, AMF3ObjectBase):
            size += AMF3ObjectPacker.size(val, str_cache=str_cache,
                                          object_cache=object_cache,
                                          traits_cache=traits_cache)

        elif isinstance(val, AMF3Date):
            size += AMF3DatePacker.size(val, cache=object_cache)

        else:
            raise ValueError("Unable to pack value of type {0}".format(type(val)))

        return size

    @classmethod
    def pack(cls, val, str_cache=None, object_cache=None, traits_cache=None):
        if str_cache is None:
            str_cache = []

        if object_cache is None:
            object_cache = []

        if traits_cache is None:
            traits_cache = []

        chunks = []

        if isinstance(val, bool):
            if val is False:
                chunks.append(U8(AMF3_TYPE_FALSE))
            elif val is True:
                chunks.append(U8(AMF3_TYPE_TRUE))

        elif val is None:
            chunks.append(U8(AMF3_TYPE_NULL))

        elif isinstance(val, integer_types):
            if val < AMF3_MIN_INTEGER or val > AMF3_MAX_INTEGER:
                chunks.append(U8(AMF3_TYPE_DOUBLE))
                chunks.append(AMF3Double(val))
            else:
                chunks.append(U8(AMF3_TYPE_INTEGER))
                chunks.append(AMF3Integer(val))

        elif isinstance(val, float):
            chunks.append(U8(AMF3_TYPE_DOUBLE))
            chunks.append(AMF3Double(val))

        elif isinstance(val, (AMF3Array, list)):
            chunks.append(U8(AMF3_TYPE_ARRAY))
            chunks.append(AMF3ArrayPacker.pack(val, str_cache=str_cache,
                                               object_cache=object_cache,
                                               traits_cache=traits_cache))

        elif isinstance(val, string_types):
            chunks.append(U8(AMF3_TYPE_STRING))
            chunks.append(AMF3String.pack(val, cache=str_cache))

        elif isinstance(val, AMF3ObjectBase):
            chunks.append(U8(AMF3_TYPE_OBJECT))
            chunks.append(AMF3ObjectPacker.pack(val, str_cache=str_cache,
                                                object_cache=object_cache,
                                                traits_cache=traits_cache))

        elif isinstance(val, AMF3Date):
            chunks.append(U8(AMF3_TYPE_DATE))
            chunks.append(AMF3DatePacker.pack(val, cache=object_cache))

        else:
            raise ValueError("Unable to pack value of type {0}".format(type(val)))

        return b"".join(chunks)

    @classmethod
    def read(cls, fd, str_cache=None, object_cache=None, traits_cache=None):
        type_ = U8.read(fd)

        if str_cache is None:
            str_cache = []

        if object_cache is None:
            object_cache = []

        if traits_cache is None:
            traits_cache = []

        if type_ == AMF3_TYPE_UNDEFINED or type_ == AMF3_TYPE_NULL:
            return None

        elif type_ == AMF3_TYPE_FALSE:
            return False

        elif type_ == AMF3_TYPE_TRUE:
            return True

        elif type_ == AMF3_TYPE_STRING:
            return AMF3String.read(fd, cache=str_cache)

        elif type_ == AMF3_TYPE_ARRAY:
            return AMF3ArrayPacker.read(fd, str_cache=str_cache,
                                        object_cache=object_cache,
                                        traits_cache=traits_cache)

        elif type_ == AMF3_TYPE_OBJECT:
            return AMF3ObjectPacker.read(fd, str_cache=str_cache, object_cache=object_cache,
                                         traits_cache=traits_cache)

        elif type_ == AMF3_TYPE_DATE:
            return AMF3DatePacker.read(fd, cache=object_cache)

        elif type_ in cls.Readers:
            return cls.Readers[type_].read(fd)

        else:
            raise IOError("Unhandled AMF3 type: {0}".format(hex(type_)))
