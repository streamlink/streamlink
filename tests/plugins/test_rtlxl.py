from streamlink.plugins.rtlxl import RTLxl
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlrtlxl(PluginCanHandleUrl):
    __plugin__ = RTLxl

    should_match = [
        'https://www.rtl.nl/video/206a0db0-9bc8-3a32-bda3-e9b3a9d4d377/',
    ]

    should_not_match = [
        'https://www.rtl.nl/',
    ]
