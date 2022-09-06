from streamlink.plugins.vkplay import VKPlay
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVK(PluginCanHandleUrl):
    __plugin__ = VKPlay

    should_match = [
        "https://vkplay.live/dmitry_live",
        "https://vkplay.live/dmitry_live/streams/video_stream?share=stream_link",
    ]

    should_not_match = [
        "https://vkplay.live",
        "https://vkplay.live/",
    ]
