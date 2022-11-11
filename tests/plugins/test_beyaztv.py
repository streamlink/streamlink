from streamlink.plugins.beyaztv import BeyazTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBeyazTV(PluginCanHandleUrl):
    __plugin__ = BeyazTV

    should_match = [
        "https://www.beyaztv.com.tr/canli-yayin",
        "https://m.beyaztv.com.tr/canli-yayin/",
    ]

    should_not_match = [
        # http error 404
        "https://m.beyaztv.com.tr/canli-yayin",
    ]
