from .error import AMFError
from .packet import Packet
from .types import AMF0String, AMF0Value, U8, U16BE, U32BE


class AMFHeader(Packet):
    exception = AMFError

    def __init__(self, name, value, must_understand=False):
        self.name = name
        self.value = value
        self.must_understand = must_understand

    @property
    def size(self):
        size = 4 + 1
        size += AMF0String.size(self.name)
        size += AMF0Value.size(self.value)

        return size

    def _serialize(self, packet):
        packet += AMF0String(self.name)
        packet += U8(int(self.must_understand))
        packet += U32BE(self.size)
        packet += AMF0Value(self.value)

    @classmethod
    def _deserialize(cls, io):
        name = AMF0String.read(io)
        must_understand = bool(U8.read(io))
        length = U32BE.read(io)
        value = AMF0Value.read(io)

        return cls(name, value, must_understand)


class AMFMessage(Packet):
    exception = AMFError

    def __init__(self, target_uri, response_uri, value):
        self.target_uri = target_uri
        self.response_uri = response_uri
        self.value = value

    @property
    def size(self):
        size = 4
        size += AMF0String.size(self.target_uri)
        size += AMF0String.size(self.response_uri)
        size += AMF0Value.size(self.value)

        return size

    def _serialize(self, packet):
        packet += AMF0String(self.target_uri)
        packet += AMF0String(self.response_uri)
        packet += U32BE(AMF0Value.size(self.value))
        packet += AMF0Value.pack(self.value)

    @classmethod
    def _deserialize(cls, io):
        target_uri = AMF0String.read(io)
        response_uri = AMF0String.read(io)
        length = U32BE.read(io)
        value = AMF0Value.read(io)

        return cls(target_uri, response_uri, value)


class AMFPacket(Packet):
    exception = AMFError

    def __init__(self, version, headers=None, messages=None):
        if headers is None:
            headers = []

        if messages is None:
            messages = []

        self.version = version
        self.headers = headers
        self.messages = messages

    @property
    def size(self):
        size = 2 + 2 + 2

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

        if version not in (0, 3):
            raise AMFError("AMF version must be 0 or 3")

        headers = []
        header_count = U16BE.read(io)

        for i in range(header_count):
            header = AMFHeader.deserialize(io)
            headers.append(header)

        messages = []
        message_count = U16BE.read(io)
        for i in range(message_count):
            message = AMFMessage.deserialize(io)
            messages.append(message)

        return cls(version, headers, messages)


__all__ = ["AMFPacket", "AMFHeader", "AMFMessage"]
