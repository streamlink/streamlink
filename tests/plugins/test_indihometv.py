from streamlink.plugins.indihometv import IndiHomeTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlIndiHomeTV(PluginCanHandleUrl):
    __plugin__ = IndiHomeTV

    should_match = [
        "https://www.indihometv.com/livetv/seatoday",
        "https://www.indihometv.com/livetv/transtv",
        "https://www.indihometv.com/tvod/seatoday/1680109200/1680111000/18328552/voa-our-voice",
    ]
