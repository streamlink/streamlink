import re
from io import BytesIO

from streamlink import NoStreamsError
from streamlink.options import Options
from streamlink.plugin import PluginArgument, PluginArguments, pluginmatcher
from streamlink.plugins import Plugin
from streamlink.stream import AkamaiHDStream, HLSStream, HTTPStream, RTMPStream, Stream


class TestStream(Stream):
    __shortname__ = "test"

    def open(self):
        return BytesIO(b'x' * 8192 * 2)


@pluginmatcher(re.compile(
    r"https?://test\.se"
))
class TestPlugin(Plugin):
    arguments = PluginArguments(
        PluginArgument(
            "bool",
            action="store_true"
        ),
        PluginArgument(
            "password",
            metavar="PASSWORD",
            sensitive=True
        )
    )

    options = Options({
        "a_option": "default"
    })

    author = "Tѥst Āuƭhǿr"
    category = None
    title = "Test Title"

    def _get_streams(self):
        if "empty" in self.url:
            return

        if "UnsortableStreamNames" in self.url:
            def gen():
                for i in range(3):
                    yield "vod", HTTPStream(self.session, "http://test.se/stream")

            return gen()

        if "NoStreamsError" in self.url:
            raise NoStreamsError(self.url)

        streams = {}
        streams["test"] = TestStream(self.session)
        streams["rtmp"] = RTMPStream(self.session, dict(rtmp="rtmp://test.se"))
        streams["hls"] = HLSStream(self.session, "http://test.se/playlist.m3u8")
        streams["http"] = HTTPStream(self.session, "http://test.se/stream")
        streams["akamaihd"] = AkamaiHDStream(self.session, "http://test.se/stream")

        streams["240p"] = HTTPStream(self.session, "http://test.se/stream")
        streams["360p"] = HTTPStream(self.session, "http://test.se/stream")
        streams["1080p"] = HTTPStream(self.session, "http://test.se/stream")

        streams["350k"] = HTTPStream(self.session, "http://test.se/stream")
        streams["800k"] = HTTPStream(self.session, "http://test.se/stream")
        streams["1500k"] = HTTPStream(self.session, "http://test.se/stream")
        streams["3000k"] = HTTPStream(self.session, "http://test.se/stream")

        streams["480p"] = [HTTPStream(self.session, "http://test.se/stream"),
                           RTMPStream(self.session, dict(rtmp="rtmp://test.se"))]

        return streams


__plugin__ = TestPlugin
