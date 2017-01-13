#!/usr/bin/env python

from ctypes import BigEndianStructure, Union, c_uint8
from io import BytesIO

from .compat import *
from .error import *
from .packet import *
from .types import *
from .util import *

TAG_TYPE_AUDIO = 8
TAG_TYPE_VIDEO = 9
TAG_TYPE_SCRIPT = 18

AUDIO_CODEC_ID_PCM = 0
AUDIO_CODEC_ID_ADPCM = 1
AUDIO_CODEC_ID_MP3 = 2
AUDIO_CODEC_ID_PCM_LE = 3
AUDIO_CODEC_ID_NELLYMOSSER_16 = 4
AUDIO_CODEC_ID_NELLYMOSSER_8 = 5
AUDIO_CODEC_ID_NELLYMOSSER = 6
AUDIO_CODEC_ID_G711_A = 7
AUDIO_CODEC_ID_G711_MU = 8
AUDIO_CODEC_ID_AAC = 10
AUDIO_CODEC_ID_SPEEX = 11
AUDIO_CODEC_ID_MP3_8 = 14
AUDIO_CODEC_ID_DEVICE = 15

AUDIO_RATE_5_5_KHZ = 0
AUDIO_RATE_11_KHZ = 1
AUDIO_RATE_22_KHZ = 2
AUDIO_RATE_44_KHZ = 3

AUDIO_BIT_RATE_8 = 0
AUDIO_BIT_RATE_16 = 1

AUDIO_TYPE_MONO = 0
AUDIO_TYPE_STEREO = 1

AAC_PACKET_TYPE_SEQUENCE_HEADER = 0
AAC_PACKET_TYPE_RAW = 1

VIDEO_FRAME_TYPE_KEY_FRAME = 1
VIDEO_FRAME_TYPE_INTER_FRAME = 2
VIDEO_FRAME_TYPE_DIS_INTER_FRAME = 3
VIDEO_FRAME_TYPE_GEN_KEY_FRAME = 4
VIDEO_FRAME_TYPE_COMMAND_FRAME = 5

VIDEO_CODEC_ID_H263 = 2
VIDEO_CODEC_ID_SCREEN_VIDEO = 3
VIDEO_CODEC_ID_VP6 = 4
VIDEO_CODEC_ID_VP6A = 5
VIDEO_CODEC_ID_SCREEN_VIDEO_2 = 6
VIDEO_CODEC_ID_AVC = 7

AVC_PACKET_TYPE_SEQUENCE_HEADER = 0
AVC_PACKET_TYPE_NALU = 1
AVC_PACKET_TYPE_END_OF_SEQUENCE = 2


class TypeFlags(Union):
    class Bits(BigEndianStructure):
        _fields_ = [("rsv1", c_uint8, 5),
                    ("audio", c_uint8, 1),
                    ("rsv2", c_uint8, 1),
                    ("video", c_uint8, 1)]

    _fields_ = [("bit", Bits), ("byte", c_uint8)]


class TagFlags(Union):
    class Bits(BigEndianStructure):
        _fields_ = [("rsv", c_uint8, 2),
                    ("filter", c_uint8, 1),
                    ("type", c_uint8, 5)]

    _fields_ = [("bit", Bits), ("byte", c_uint8)]


class AudioFlags(Union):
    class Bits(BigEndianStructure):
        _fields_ = [("codec", c_uint8, 4),
                    ("rate", c_uint8, 2),
                    ("bits", c_uint8, 1),
                    ("type", c_uint8, 1)]

    _fields_ = [("bit", Bits), ("byte", c_uint8)]


class VideoFlags(Union):
    class Bits(BigEndianStructure):
        _fields_ = [("type", c_uint8, 4),
                    ("codec", c_uint8, 4)]

    _fields_ = [("bit", Bits), ("byte", c_uint8)]


class Header(Packet):
    exception = FLVError

    def __init__(self, version=1, has_audio=False, has_video=False, data_offset=9, tag0_size=0):
        self.version = version
        self.flags = TypeFlags()
        self.flags.bit.audio = int(has_audio)
        self.flags.bit.video = int(has_video)
        self.data_offset = data_offset
        self.tag0_size = tag0_size

    def __repr__(self):
        reprformat = "<Header version={version} has_audio={has_audio} has_video={has_video} data_offset={offset}>"
        return reprformat.format(version=self.version, offset=self.data_offset,
                                 has_audio=self.has_audio, has_video=self.has_video)

    @property
    def size(self):
        return 13

    has_audio = flagproperty("flags", "audio", True)
    has_video = flagproperty("flags", "video", True)

    @classmethod
    def _deserialize(cls, io):
        head = io.read(3)

        if head != b"FLV":
            raise FLVError("Invalid FLV header")

        version = U8.read(io)
        flags = TypeFlags()
        flags.byte = U8.read(io)
        offset = U32BE.read(io)
        tag0_size = U32BE.read(io)

        return Header(version, bool(flags.bit.audio), bool(flags.bit.video),
                      offset, tag0_size)

    @classmethod
    def _deserialize_from(cls, buf, offset):
        head = buf[offset:offset + 3]
        offset += 3

        if head != b"FLV":
            raise FLVError("Invalid FLV header")

        flags = TypeFlags()

        (version, flags.byte, tag0_offset,
         tag0_size) = unpack_many_from(buf, offset, (U8, U8, U32BE, U32BE))

        rval = Header(version, bool(flags.bit.audio), bool(flags.bit.video),
                      tag0_offset, tag0_size)

        offset += 10

        return (rval, offset)

    def _serialize(self, packet):
        packet += b"FLV"
        packet += U8(self.version)
        packet += U8(self.flags.byte)
        packet += U32BE(self.data_offset)
        packet += U32BE(self.tag0_size)

    def _serialize_into(self, packet, offset):
        offset = pack_bytes_into(packet, offset, b"FLV")
        offset = pack_many_into(packet, offset,
                                (U8, U8, U32BE, U32BE),
                                (self.version, self.flags.byte,
                                 self.data_offset, self.tag0_size))

        return offset


class Tag(Packet):
    exception = FLVError

    def __init__(self, typ=TAG_TYPE_SCRIPT, timestamp=0, data=None,
                 streamid=0, filter=False, padding=None):
        self.flags = TagFlags()
        self.flags.bit.rsv = 0
        self.flags.bit.type = typ
        self.flags.bit.filter = int(filter)

        if not data:
            data = RawData()

        if not padding:
            padding = b""

        self.data = data
        self.streamid = streamid
        self.timestamp = timestamp
        self.padding = padding

    def __repr__(self):
        reprformat = "<Tag type={type} timestamp={timestamp} streamid={streamid} filter={filter} data={data}>"
        return reprformat.format(type=self.type, timestamp=self.timestamp,
                                 streamid=self.streamid, filter=self.filter,
                                 data=repr(self.data))

    type = flagproperty("flags", "type")
    filter = flagproperty("flags", "filter", True)

    @property
    def data_size(self):
        return self.data.size

    @property
    def tag_size(self):
        return 11 + self.data_size + len(self.padding)

    @property
    def size(self):
        return 4 + self.tag_size

    @classmethod
    def _deserialize(cls, io, strict=False, raw_data=False):
        header = io.read(11)

        if len(header) < 11:
            raise FLVError("Insufficient tag header")

        (flagb, data_size, timestamp, timestamp_ext,
         streamid) = unpack_many_from(header, 0, (U8, U24BE, U24BE, U8, U24BE))

        flags = TagFlags()
        flags.byte = flagb
        timestamp |= timestamp_ext << 24

        # Don't parse encrypted data
        if flags.bit.filter == 1:
            raw_data = True

        if flags.bit.type in TagDataTypes:
            datacls = TagDataTypes[flags.bit.type]
        else:
            raise FLVError("Unknown tag type!")

        tag_data = chunked_read(io, data_size, exception=FLVError)

        if data_size > 0 and not raw_data:
            tag_data_io = BytesIO(tag_data)
            data = datacls.deserialize(tag_data_io)
            padding = tag_data_io.read()
        else:
            data = RawData(tag_data)
            padding = b""

        tag = Tag(flags.bit.type, timestamp, data,
                  streamid, bool(flags.bit.filter), padding)

        tag_size = U32BE.read(io)

        if strict and tag.tag_size != tag_size:
            raise FLVError("Data size mismatch when deserialising tag")

        return tag

    @classmethod
    def _deserialize_from(cls, buf, offset, strict=False,
                          raw_data=False):
        (flagb, data_size, timestamp, timestamp_ext,
         streamid) = unpack_many_from(buf, offset, (U8, U24BE, U24BE, U8, U24BE))

        offset += 11

        flags = TagFlags()
        flags.byte = flagb
        timestamp |= timestamp_ext << 24

        # Don't parse encrypted data
        if flags.bit.filter == 1:
            raw_data = True

        if flags.bit.type in TagDataTypes:
            datacls = TagDataTypes[flags.bit.type]
        else:
            raise FLVError("Unknown tag type!")

        if data_size > 0 and not raw_data:
            data, doffset = datacls.deserialize_from(buf, offset, buf_size=data_size)
            padding = buf[doffset:offset + data_size]
        else:
            data = RawData(buf[offset:offset + data_size])
            padding = b""

        offset += data_size

        tag = Tag(flags.bit.type, timestamp, data,
                  streamid, bool(flags.bit.filter), padding)

        tag_size = U32BE.unpack_from(buf, offset)[0]
        offset += U32BE.size

        if strict and tag.tag_size != tag_size:
            raise FLVError("Data size mismatch when deserialising tag")

        return (tag, offset)

    def _serialize(self, packet, strict=True):
        packet += U8(self.flags.byte)
        packet += U24BE(self.data_size)

        packet += U24BE(self.timestamp & 0xFFFFFF)
        packet += U8((self.timestamp >> 24) & 0x7F)
        packet += U24BE(self.streamid)

        self.data.serialize(packet)
        packet += self.padding

        if strict and self.tag_size != len(packet):
            raise FLVError("Data size mismatch when serialising tag")

        packet += U32BE(self.tag_size)

    def _serialize_into(self, packet, offset):
        offset = pack_many_into(packet, offset,
                                (U8, U24BE, U24BE, U8, U24BE),
                                (self.flags.byte, self.data_size,
                                 self.timestamp & 0xFFFFFF,
                                 (self.timestamp >> 24) & 0x7F,
                                 self.streamid))

        offset = self.data.serialize_into(packet, offset)
        offset = pack_bytes_into(packet, offset, self.padding)

        U32BE.pack_into(packet, offset, self.tag_size)
        offset += 4

        return offset


class FrameData(TagData):
    def __init__(self, type=1, data=b""):
        self.type = type
        self.data = data

    def __repr__(self):
        if not isinstance(self.data, Packet):
            data = ("<{0}>").format(type(self.data).__name__)
        else:
            data = repr(self.data)

        reprformat = "<{cls} type={type} data={data}>"
        return reprformat.format(cls=type(self).__name__, type=self.type, data=data)

    @property
    def size(self):
        return TagData.size.__get__(self) + 1

    @classmethod
    def _deserialize(cls, io):
        typ = U8.read(io)
        data = io.read()

        return cls(typ, data)

    @classmethod
    def _deserialize_from(cls, buf, offset, buf_size=None):
        if not buf_size:
            buf_size = len(buf)

        typ = U8.unpack_from(buf, offset)[0]
        offset += U8.size
        buf_size -= U8.size

        data = buf[offset:offset + buf_size]
        offset += buf_size

        return (cls(typ, data), offset)

    def _serialize(self, packet):
        packet += U8(self.type)
        packet += self.data

    def _serialize_into(self, packet, offset):
        U8.pack_into(packet, offset, self.type)
        offset += U8.size
        offset = pack_bytes_into(packet, offset, self.data)

        return offset


class RawData(TagData):
    def __init__(self, data=None):
        if not data:
            data = b""

        self.data = data

    def __repr__(self):
        return "<RawData>"

    @classmethod
    def _deserialize(cls, io):
        return cls(io.read())

    @classmethod
    def _deserialize_from(cls, buf, offset, buf_size=None):
        if not data_size:
            buf_size = len(buf)

        data = buf[offset:offset + buf_size]
        rval = cls(data)
        offset += len(data)

        return (rval, offset)

    def _serialize(self, packet):
        packet += self.data

    def _serialize_into(self, packet, offset):
        return pack_bytes_into(packet, offset, self.data)


class AudioData(TagData):
    def __init__(self, codec=0, rate=0, bits=0, type=0, data=None):
        self.flags = AudioFlags()
        self.flags.bit.codec = codec
        self.flags.bit.rate = rate
        self.flags.bit.bits = bits
        self.flags.bit.type = type
        self.data = data

    codec = flagproperty("flags", "codec")
    rate = flagproperty("flags", "rate")
    bits = flagproperty("flags", "bits")
    type = flagproperty("flags", "type")

    def __repr__(self):
        if not isinstance(self.data, Packet):
            data = ("<{0}>").format(type(self.data).__name__)
        else:
            data = repr(self.data)

        reprformat = "<AudioData type={type} codec={codec} rate={rate} bits={bits} data={data}>"
        return reprformat.format(type=self.type, codec=self.codec, rate=self.rate,
                                 bits=self.bits, data=data)

    @property
    def size(self):
        return TagData.size.__get__(self) + 1

    @classmethod
    def _deserialize(cls, io):
        flags = AudioFlags()
        flags.byte = U8.read(io)

        if flags.bit.codec == AUDIO_CODEC_ID_AAC:
            data = AACAudioData.deserialize(io)
        else:
            data = io.read()

        return cls(flags.bit.codec, flags.bit.rate, flags.bit.bits,
                   flags.bit.type, data)

    @classmethod
    def _deserialize_from(cls, buf, offset, buf_size=None):
        if not buf_size:
            buf_size = len(buf)

        flags = AudioFlags()
        flags.byte = U8.unpack_from(buf, offset)[0]
        offset += U8.size
        buf_size -= U8.size

        if flags.bit.codec == 10:
            data, offset = AACAudioData.deserialize_from(buf, offset,
                                                         buf_size=buf_size)
        else:
            data = buf[offset:offset + buf_size]
            offset += buf_size

        obj = cls(flags.bit.codec, flags.bit.rate, flags.bit.bits,
                  flags.bit.type, data)

        return (obj, offset)

    def _serialize(self, packet):
        packet += U8(self.flags.byte)

        if isinstance(self.data, Packet):
            self.data.serialize(packet)
        else:
            packet += self.data

    def _serialize_into(self, packet, offset):
        U8.pack_into(packet, offset, self.flags.byte)
        offset += 1

        if isinstance(self.data, Packet):
            offset = self.data.serialize_into(packet, offset)
        else:
            offset = pack_bytes_into(packet, offset, self.data)

        return offset


class AACAudioData(FrameData):
    pass


class VideoData(TagData):
    def __init__(self, type=0, codec=0, data=None):
        self.flags = VideoFlags()
        self.flags.bit.type = type
        self.flags.bit.codec = codec

        if not data:
            data = b""

        self.data = data

    def __repr__(self):
        if not isinstance(self.data, Packet):
            data = ("<{0}>").format(type(self.data).__name__)
        else:
            data = repr(self.data)

        reprformat = "<VideoData type={type} codec={codec} data={data}>"
        return reprformat.format(type=self.type, codec=self.codec, data=data)

    type = flagproperty("flags", "type")
    codec = flagproperty("flags", "codec")

    @property
    def size(self):
        return TagData.size.__get__(self) + 1

    @classmethod
    def _deserialize(cls, io):
        flags = VideoFlags()
        flags.byte = U8.read(io)

        if flags.bit.type == VIDEO_FRAME_TYPE_COMMAND_FRAME:
            data = VideoCommandFrame.deserialize(io)
        else:
            if flags.bit.codec == VIDEO_CODEC_ID_AVC:
                data = AVCVideoData.deserialize(io)
            else:
                data = io.read()

        return cls(flags.bit.type, flags.bit.codec, data)

    @classmethod
    def _deserialize_from(cls, buf, offset, buf_size=None):
        if not buf_size:
            buf_size = len(buf)

        flags = VideoFlags()
        flags.byte = U8.unpack_from(buf, offset)[0]
        offset += U8.size
        buf_size -= U8.size

        if flags.bit.type == VIDEO_FRAME_TYPE_COMMAND_FRAME:
            data, offset = VideoCommandFrame.deserialize_from(buf, offset,
                                                              buf_size=buf_size)
        else:
            if flags.bit.codec == VIDEO_CODEC_ID_AVC:
                data, offset = AVCVideoData.deserialize_from(buf, offset,
                                                             buf_size=buf_size)
            else:
                data = buf[offset:offset + buf_size]
                offset += buf_size

        obj = cls(flags.bit.type, flags.bit.codec, data)

        return (obj, offset)

    def _serialize(self, packet):
        packet += U8(self.flags.byte)

        if isinstance(self.data, Packet):
            self.data.serialize(packet)
        else:
            packet += self.data

    def _serialize_into(self, packet, offset):
        U8.pack_into(packet, offset, self.flags.byte)
        offset += 1

        if isinstance(self.data, Packet):
            offset = self.data.serialize_into(packet, offset)
        else:
            offset = pack_bytes_into(packet, offset, self.data)

        return offset


class VideoCommandFrame(FrameData):
    pass


class AVCVideoData(TagData):
    def __init__(self, type=1, composition_time=0, data=None):
        self.type = type
        self.composition_time = composition_time

        if not data:
            data = b""

        self.data = data

    def __repr__(self):
        if not isinstance(self.data, Packet):
            data = ("<{0}>").format(type(self.data).__name__)
        else:
            data = repr(self.data)

        reprformat = "<AVCVideoData type={type} composition_time={composition_time} data={data}>"
        return reprformat.format(type=self.type, composition_time=self.composition_time,
                                 data=data)

    @property
    def size(self):
        return TagData.size.__get__(self) + 4

    @classmethod
    def _deserialize(cls, io):
        typ = U8.read(io)
        composition_time = S24BE.read(io)
        data = io.read()

        return cls(typ, composition_time, data)

    @classmethod
    def _deserialize_from(cls, buf, offset, buf_size=None):
        if not buf_size:
            buf_size = None

        typ = U8.unpack_from(buf, offset)[0]
        offset += U8.size

        composition_time = S24BE.unpack_from(buf, offset)[0]
        offset += S24BE.size

        buf_size -= U8.size + S24BE.size
        data = buf[offset:offset + buf_size]
        offset += len(data)

        obj = cls(typ, composition_time, data)

        return (obj, offset)

    def _serialize(self, packet):
        packet += U8(self.type)
        packet += S24BE(self.composition_time)
        packet += self.data

    def _serialize_into(self, packet, offset):
        offset = pack_many_into(packet, offset,
                                (U8, S24BE),
                                (self.type, self.composition_time))

        offset = pack_bytes_into(packet, offset, self.data)

        return offset


class ScriptData(TagData):
    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value

    def __repr__(self):
        reprformat = "<ScriptData name={name} value={value}>"
        return reprformat.format(name=self.name, value=self.value)

    @property
    def size(self):
        size = ScriptDataValue.size(self.name)
        size += ScriptDataValue.size(self.value)

        return size

    @classmethod
    def _deserialize(cls, io):
        name = ScriptDataValue.read(io)
        value = ScriptDataValue.read(io)

        return ScriptData(name, value)

    @classmethod
    def _deserialize_from(cls, buf, offset, buf_size=None):
        name, offset = ScriptDataValue.unpack_from(buf, offset)
        value, offset = ScriptDataValue.unpack_from(buf, offset)

        return (ScriptData(name, value), offset)

    def _serialize(self, packet):
        packet += ScriptDataValue.pack(self.name)
        packet += ScriptDataValue.pack(self.value)

    def _serialize_into(self, packet, offset):
        offset = ScriptDataValue.pack_into(packet, offset, self.name)
        offset = ScriptDataValue.pack_into(packet, offset, self.value)

        return offset


TagDataTypes = {
    TAG_TYPE_AUDIO: AudioData,
    TAG_TYPE_VIDEO: VideoData,
    TAG_TYPE_SCRIPT: ScriptData
}


__all__ = ["Header", "Tag", "FrameData", "AudioData", "AACAudioData",
           "VideoData", "VideoCommandFrame", "AVCVideoData",
           "ScriptData", "TAG_TYPE_VIDEO", "TAG_TYPE_AUDIO", "TAG_TYPE_SCRIPT"]
