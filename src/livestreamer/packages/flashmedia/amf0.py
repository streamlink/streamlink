from .compat import *
from .error import *
from .packet import *
from .util import *

class AMF0Header(Packet):
    def __init__(self, name, value, must_understand=False):
        self.name = name
        self.value = value
        self.must_understand = must_understand

    @property
    def size(self):
        size = 4+1
        size += PacketIO.script_string_size(self.name)
        size += PacketIO.script_value_size(self.value)

        return size

    def _serialize(self, packet):
        packet.write_script_string(self.name)
        packet.write_u8(int(self.must_understand))
        packet.write_u32(self.size)
        packet.write_script_value(self.value)

    @classmethod
    def _deserialize(cls, io):
        name = io.read_script_string()
        must_understand = bool(io.read_u8())
        length = io.read_u32()
        value = io.read_script_value()

        return cls(name, value, must_understand)


class AMF0Message(Packet):
    def __init__(self, target_uri, response_uri, value):
        self.target_uri = target_uri
        self.response_uri = response_uri
        self.value = value

    @property
    def size(self):
        size = 4
        size += PacketIO.script_string_size(self.target_uri)
        size += PacketIO.script_string_size(self.response_uri)
        size += PacketIO.script_value_size(self.value)

        return size

    def _serialize(self, packet):
        packet.write_script_string(self.target_uri)
        packet.write_script_string(self.response_uri)
        packet.write_u32(self.size)
        packet.write_script_value(self.value)

    @classmethod
    def _deserialize(cls, io):
        target_uri = io.read_script_string()
        response_uri = io.read_script_string()
        length = io.read_u32()
        value = io.read_script_value()


        return cls(target_uri, response_uri, value)


class AMF0Packet(Packet):
    def __init__(self, version, headers=[], messages=[]):
        self.version = version
        self.headers = headers
        self.messages = messages

    @property
    def size(self):
        size = 2+2+2

        for header in self.headers:
            size += header.size

        for message in self.messages:
            size += message.size

        return size

    def _serialize(self, packet):
        packet.write_u16(self.version)
        packet.write_u16(len(self.headers))

        for header in self.headers:
            header.serialize(packet)

        packet.write_u16(len(self.messages))
        for message in self.messages:
            message.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = io.read_u16()

        if version != 0:
            raise AMFError("AMF version must be 0")

        headers = []
        header_count = io.read_u16()

        for i in range(header_count):
            header = AMF0Header.deserialize(io=io)
            headers.append(header)

        messages = []
        message_count = io.read_u16()
        for i in range(message_count):
            message = AMF0Message.deserialize(io=io)
            messages.append(message)

        return cls(version, headers, messages)

__all__ = ["AMF0Packet", "AMF0Header", "AMF0Message"]
