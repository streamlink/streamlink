import base64
import io
import hashlib
import hmac
import random

from .stream import Stream
from .wrappers import StreamIOThreadWrapper, StreamIOIterWrapper

from ..buffers import Buffer
from ..compat import str, bytes, urlparse
from ..exceptions import StreamError
from ..utils import swfdecompress

from ..packages.flashmedia import FLV, FLVError
from ..packages.flashmedia.tag import ScriptData


class TokenGenerator(object):
    def __init__(self, stream):
        self.stream = stream

    def generate(self):
        raise NotImplementedError


class Auth3TokenGenerator(TokenGenerator):
    def generate(self):
        if not self.stream.swf:
            raise StreamError("A SWF URL is required to create session token")

        res = self.stream.session.http.get(self.stream.swf,
                                           exception=StreamError)
        data = swfdecompress(res.content)

        md5 = hashlib.md5()
        md5.update(data)

        data = bytes(self.stream.sessionid, "ascii") + md5.digest()
        sig = hmac.new(b"foo", data, hashlib.sha1)
        b64 = base64.encodestring(sig.digest())
        token = str(b64, "ascii").replace("\n", "")

        return token


def cache_bust_string(length):
    rval = ""

    for i in range(length):
        rval += chr(65 + int(round(random.random() * 25)))

    return rval


class AkamaiHDStreamIO(io.IOBase):
    Version = "2.5.8"
    FlashVersion = "LNX 11,1,102,63"

    StreamURLFormat = "{host}/{streamname}"
    ControlURLFormat = "{host}/control/{streamname}"
    ControlData = b":)"

    TokenGenerators = {
        "c11e59dea648d56e864fc07a19f717b9": Auth3TokenGenerator
    }

    StatusComplete = 3
    StatusError = 4

    Errors = {
        1: "Stream not found",
        2: "Track not found",
        3: "Seek out of bounds",
        4: "Authentication failed",
        5: "DVR disabled",
        6: "Invalid bitrate test"
    }

    def __init__(self, session, url, swf=None, seek=None):
        parsed = urlparse(url)

        self.session = session
        self.logger = self.session.logger.new_module("stream.akamaihd")
        self.host = ("{scheme}://{netloc}").format(scheme=parsed.scheme, netloc=parsed.netloc)
        self.streamname = parsed.path[1:]
        self.swf = swf
        self.seek = seek

    def open(self):
        self.guid = cache_bust_string(12)
        self.islive = None
        self.sessionid = None
        self.flv = None

        self.buffer = Buffer()
        self.completed_handshake = False

        url = self.StreamURLFormat.format(host=self.host, streamname=self.streamname)
        params = self._create_params(seek=self.seek)

        self.logger.debug("Opening host={host} streamname={streamname}",
                          host=self.host, streamname=self.streamname)

        try:
            res = self.session.http.get(url, stream=True, params=params)
            self.fd = StreamIOIterWrapper(res.iter_content(8192))
        except Exception as err:
            raise StreamError(str(err))

        self.handshake(self.fd)

        return self

    def handshake(self, fd):
        try:
            self.flv = FLV(fd)
        except FLVError as err:
            raise StreamError(str(err))

        self.buffer.write(self.flv.header.serialize())
        self.logger.debug("Attempting to handshake")

        for i, tag in enumerate(self.flv):
            if i == 10:
                raise StreamError("No OnEdge metadata in FLV after 10 tags, probably not a AkamaiHD stream")

            self.process_tag(tag, exception=StreamError)

            if self.completed_handshake:
                self.logger.debug("Handshake successful")
                break

    def process_tag(self, tag, exception=IOError):
        if isinstance(tag.data, ScriptData) and tag.data.name == "onEdge":
            self._on_edge(tag.data.value, exception=exception)

        self.buffer.write(tag.serialize())

    def send_token(self, token):
        headers = { "x-Akamai-Streaming-SessionToken": token }

        self.logger.debug("Sending new session token")
        self.send_control("sendingNewToken", headers=headers,
                          swf=self.swf)

    def send_control(self, cmd, headers=None, **params):
        if not headers:
            headers = {}

        url = self.ControlURLFormat.format(host=self.host,
                                           streamname=self.streamname)

        headers["x-Akamai-Streaming-SessionID"] = self.sessionid

        params = self._create_params(cmd=cmd, **params)

        return self.session.http.post(url,
                                      headers=headers,
                                      params=params,
                                      data=self.ControlData,
                                      exception=StreamError)

    def read(self, size=-1):
        if not (self.flv and self.fd):
            return b""

        if self.buffer.length:
            return self.buffer.read(size)
        else:
            return self.fd.read(size)

    def _create_params(self, **extra):
        params = dict(v=self.Version, fp=self.FlashVersion,
                      r=cache_bust_string(5), g=self.guid)
        params.update(extra)

        return params

    def _generate_session_token(self, data64):
        swfdata = base64.decodestring(bytes(data64, "ascii"))
        md5 = hashlib.md5()
        md5.update(swfdata)
        hash = md5.hexdigest()

        if hash in self.TokenGenerators:
            generator = self.TokenGenerators[hash](self)

            return generator.generate()
        else:
            raise StreamError(("No token generator available for hash '{0}'").format(hash))

    def _on_edge(self, data, exception=IOError):
        def updateattr(attr, key):
            if key in data:
                setattr(self, attr, data[key])

        self.logger.debug("onEdge data")
        for key, val in data.items():
            if isinstance(val, str):
                val = val[:50]

            self.logger.debug(" {key}={val}",
                              key=key, val=val)

        updateattr("islive", "isLive")
        updateattr("sessionid", "session")
        updateattr("status", "status")
        updateattr("streamname", "streamName")

        if self.status == self.StatusComplete:
            self.flv = None
        elif self.status == self.StatusError:
            errornum = data["errorNumber"]

            if errornum in self.Errors:
                msg = self.Errors[errornum]
            else:
                msg = "Unknown error"

            raise exception("onEdge error: " + msg)

        if not self.completed_handshake:
            if "data64" in data:
                sessiontoken = self._generate_session_token(data["data64"])
            else:
                sessiontoken = None

            self.send_token(sessiontoken)
            self.completed_handshake = True


class AkamaiHDStream(Stream):
    """
    Implements the AkamaiHD Adaptive Streaming protocol

    *Attributes:*

    - :attr:`url` URL to the stream
    - :attr:`swf` URL to a SWF used by the handshake protocol
    - :attr:`seek` Position to seek to when opening the stream
    """

    __shortname__ = "akamaihd"

    def __init__(self, session, url, swf=None, seek=None):
        Stream.__init__(self, session)

        self.seek = seek
        self.swf = swf
        self.url = url

    def __repr__(self):
        return ("<AkamaiHDStream({0!r}, "
                "swf={1!r})>".format(self.url, self.swf))

    def __json__(self):
        return dict(type=AkamaiHDStream.shortname(),
                    url=self.url, swf=self.swf)

    def open(self):
        stream = AkamaiHDStreamIO(self.session, self.url,
                                  self.swf, self.seek)

        return StreamIOThreadWrapper(self.session, stream.open())

__all__ = ["AkamaiHDStream"]
