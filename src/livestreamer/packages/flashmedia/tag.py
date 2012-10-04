#!/usr/bin/env python

from ctypes import BigEndianStructure, Union, c_uint8

from .compat import *
from .error import *
from .packet import *
from .util import *

TAG_TYPE_AUDIO = 8
TAG_TYPE_VIDEO = 9
TAG_TYPE_SCRIPT = 18

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


    has_audio = flagproperty("flags", "audio", True)
    has_video = flagproperty("flags", "video", True)

    @classmethod
    def _deserialize(cls, io):
        head = io.read(3)

        if head != b"FLV":
            raise FLVError("Invalid FLV header")

        version = io.read_u8()
        flags = TypeFlags()
        flags.byte = io.read_u8()
        offset = io.read_u32()
        tag0_size = io.read_u32()

        return Header(version, bool(flags.bit.audio), bool(flags.bit.video),
                      offset, tag0_size)

    def _serialize(self, packet):
        packet.write(b"FLV")
        packet.write_u8(self.version)
        packet.write_u8(self.flags.byte)
        packet.write_u32(self.data_offset)
        packet.write_u32(self.tag0_size)


class Tag(Packet):
    def __init__(self, typ=TAG_TYPE_SCRIPT, timestamp=0, data=None, streamid=0, filter=False):
        self.flags = TagFlags()
        self.flags.bit.rsv = 0
        self.flags.bit.type = typ
        self.flags.bit.filter = int(filter)

        self.data = data
        self.streamid = streamid
        self.timestamp = timestamp

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
        return 11 + self.data_size

    @classmethod
    def _deserialize(cls, io):
        flags  = TagFlags()
        flags.byte = io.read_u8()
        data_size = io.read_u24()
        timestamp = io.read_s32e()
        streamid = io.read_u24()

        if flags.bit.filter == 1:
            raise FLVError("Encrypted tags are not supported")

        if flags.bit.type in TagDataTypes:
            datacls = TagDataTypes[flags.bit.type]
        else:
            raise FLVError("Unknown tag type!")

        if data_size > 0:
            io.data_left = data_size
            data = datacls.deserialize(io=io)
            io.data_left = None
        else:
            data = EmptyData()

        tag = Tag(flags.bit.type, timestamp, data,
                  streamid, bool(flags.bit.filter))

        tag_size = io.read_u32()

        if tag.tag_size != tag_size:
            raise FLVError("Data size mismatch when deserialising tag")

        return tag

    def _serialize(self, packet):
        packet.write_u8(self.flags.byte)
        packet.write_u24(self.data_size)
        packet.write_s32e(self.timestamp)
        packet.write_u24(self.streamid)

        self.data.serialize(packet)

        if self.tag_size != packet.written:
            raise FLVError("Data size mismatch when serialising tag")

        packet.write_u32(packet.written)


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
        typ = io.read_u8()
        data = io.read()

        return cls(typ, data)

    def _serialize(self, packet):
        packet.write_u8(self.type)
        packet.write(self.data)


class EmptyData(TagData):
    def __init__(self):
        self.data = b""

    def __repr__(self):
        return "<EmptyData>"

    @classmethod
    def _deserialize(cls, io):
        return EmptyData()

    def _serialize(self, packet):
        packet.write(self.data)


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
        flags.byte = io.read_u8()

        if flags.bit.codec == 10:
            data = AACAudioData.deserialize(io)
        else:
            data = io.read()

        return cls(flags.bit.codec, flags.bit.rate, flags.bit.bits,
                   flags.bit.type, data)

    def _serialize(self, packet):
        packet.write_u8(self.flags.byte)

        if isinstance(self.data, Packet):
            self.data.serialize(packet)
        else:
            packet.write(self.data)


class AACAudioData(FrameData):
    pass


class VideoData(TagData):
    def __init__(self, type=0, codec=0, data=b""):
        self.flags = VideoFlags()
        self.flags.bit.type = type
        self.flags.bit.codec = codec
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
        flags.byte = io.read_u8()

        if flags.bit.type == 5:
            data = VideoCommandFrame.deserialize(io)
        else:
            if flags.bit.codec == 7:
                data = AVCVideoData.deserialize(io)
            else:
                data = io.read()

        return cls(flags.bit.type, flags.bit.codec, data)

    def _serialize(self, packet):
        packet.write_u8(self.flags.byte)

        if isinstance(self.data, Packet):
            self.data.serialize(packet)
        else:
            packet.write(self.data)


class VideoCommandFrame(FrameData):
    pass


class AVCVideoData(TagData):
    def __init__(self, type=1, composition_time=0, data=b""):
        self.type = type
        self.composition_time = composition_time
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
        typ = io.read_u8()
        composition_time = io.read_s24()
        data = io.read()

        return cls(typ, composition_time, data)

    def _serialize(self, packet):
        packet.write_u8(self.type)
        packet.write_s24(self.composition_time)
        packet.write(self.data)


class ScriptData(TagData):
    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value

    def __repr__(self):
        reprformat = "<ScriptData name={name} value={value}>"
        return reprformat.format(name=self.name, value=self.value)

    @property
    def size(self):
        size = PacketIO.script_value_size(self.name)
        size += PacketIO.script_value_size(self.value)

        return size

    @classmethod
    def _deserialize(cls, io):
        io._objects = []
        name  = io.read_script_value()
        value = io.read_script_value()

        return ScriptData(name, value)

    def _serialize(self, packet):
        packet.write_script_value(self.name)
        packet.write_script_value(self.value)


TagDataTypes = {
    TAG_TYPE_AUDIO: AudioData,
    TAG_TYPE_VIDEO: VideoData,
    TAG_TYPE_SCRIPT: ScriptData
}



__all__ = ["Header", "Tag", "FrameData", "AudioData", "AACAudioData",
           "VideoData", "VideoCommandFrame", "AVCVideoData",
           "ScriptData", "TAG_TYPE_VIDEO", "TAG_TYPE_AUDIO", "TAG_TYPE_SCRIPT"]
