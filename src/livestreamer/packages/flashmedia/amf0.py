from .compat import *
from .error import *
from .packet import *
from .types import *
from .util import *

class AMF0Header(Packet):
    def __init__(self, name, value, must_understand=False):
        self.name = name
        self.value = value
        self.must_understand = must_understand

    @property
    def size(self):
        size = 4+1
        size += ScriptDataString.size(self.name)
        size += ScriptDataValue.size(self.value)

        return size

    def _serialize(self, packet):
        packet += ScriptDataString(self.name)
        packet += U8(int(self.must_understand))
        packet += U32BE(self.size)
        packet += ScriptDataValue(self.value)

    @classmethod
    def _deserialize(cls, io):
        name = ScriptDataString.read(io)
        must_understand = bool(U8.read(io))
        length = U32BE.read(io)
        value = ScriptDataValue.read(io)

        return cls(name, value, must_understand)


class AMF0Message(Packet):
    def __init__(self, target_uri, response_uri, value):
        self.target_uri = target_uri
        self.response_uri = response_uri
        self.value = value

    @property
    def size(self):
        size = 4
        size += ScriptDataString.size(self.target_uri)
        size += ScriptDataString.size(self.response_uri)
        size += ScriptDataValue.size(self.value)

        return size

    def _serialize(self, packet):
        packet += ScriptDataString(self.target_uri)
        packet += ScriptDataString(self.response_uri)
        packet += U32BE(self.size)
        packet += ScriptDataValue(self.value)

    @classmethod
    def _deserialize(cls, io):
        target_uri = ScriptDataString.read(io)
        response_uri = ScriptDataString.read(io)
        length = U32BE.read(io)
        value = ScriptDataValue.read(io)

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
        packet += U16BE(self.version)
        packet += U16BE(len(self.headers))

        for header in self.headers:
            header.serialize(packet)

        packet += U16BE(len(self.messages))
        for message in self.messages:
            message.serialize(packet)

    @classmethod
    def _deserialize(cls, io):
        version = U16BE.read(io)

        if version != 0:
            raise AMFError("AMF version must be 0")

        headers = []
        header_count = U16BE.read(io)

        for i in range(header_count):
            header = AMF0Header.deserialize(io)
            headers.append(header)

        messages = []
        message_count = U16BE.read(io)
        for i in range(message_count):
            message = AMF0Message.deserialize(io)
            messages.append(message)

        return cls(version, headers, messages)

__all__ = ["AMF0Packet", "AMF0Header", "AMF0Message"]
