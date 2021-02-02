from streamlink.plugins.tigerdile import Tigerdile
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTigerdile(PluginCanHandleUrl):
    __plugin__ = Tigerdile

    should_match = [
        "https://www.tigerdile.com/stream/example_streamer",
        "http://www.tigerdile.com/stream/example_streamer",
        "https://www.tigerdile.com/stream/example_streamer/",
        "http://www.tigerdile.com/stream/example_streamer/",
        "https://sfw.tigerdile.com/stream/example_streamer",
        "http://sfw.tigerdile.com/stream/example_streamer",
        "https://sfw.tigerdile.com/stream/example_streamer/",
        "http://sfw.tigerdile.com/stream/example_streamer/",
    ]

    should_not_match = [
        "http://www.tigerdile.com/",
        "http://www.tigerdile.com/stream",
        "http://www.tigerdile.com/stream/",
    ]
