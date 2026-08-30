import re
from io import BytesIO

from streamlink import NoStreamsError
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.stream.stream import Stream


class TestStream(Stream):
    __shortname__ = "test"

    def open(self):
        return BytesIO(b"x" * 8192 * 2)


@pluginmatcher(
    re.compile(r"https?://test\.se"),
)
@pluginargument(
    "bool",
    action="store_true",
)
@pluginargument(
    "password",
    sensitive=True,
    metavar="PASSWORD",
)
class TestPlugin(Plugin):
    id = "test-id-1234-5678"
    author = "Tѥst Āuƭhǿr"
    category = None
    title = "Test Title"

    def _get_streams(self):
        if "empty" in self.url:
            return

        if "UnsortableStreamNames" in self.url:

            def gen():
                for _ in range(3):
                    yield "vod", HTTPStream(self.session, "http://test.se/stream")

            return gen()

        if "NoStreamsError" in self.url:
            raise NoStreamsError

        if "fromoptions" in self.url:
            return {"fromoptions": HTTPStream(self.session, self.options.get("streamurl"))}

        streams = {}
        streams["test"] = TestStream(self.session)
        streams["hls"] = HLSStream(self.session, "http://test.se/playlist.m3u8")
        streams["http"] = HTTPStream(self.session, "http://test.se/stream")

        streams["240p"] = HTTPStream(self.session, "http://test.se/stream")
        streams["360p"] = HTTPStream(self.session, "http://test.se/stream")
        streams["1080p"] = HTTPStream(self.session, "http://test.se/stream")

        streams["350k"] = HTTPStream(self.session, "http://test.se/stream")
        streams["800k"] = HTTPStream(self.session, "http://test.se/stream")
        streams["1500k"] = HTTPStream(self.session, "http://test.se/stream")
        streams["3000k"] = HTTPStream(self.session, "http://test.se/stream")

        streams["480p"] = [
            HTTPStream(self.session, "http://test.se/stream"),
            HLSStream(self.session, "http://test.se/playlist.m3u8"),
        ]

        return streams


__plugin__ = TestPlugin
