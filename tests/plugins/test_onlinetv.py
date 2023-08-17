from streamlink.plugins.vkplay import VKplay

from src.streamlink.plugins.onlinetv import OnlineTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlOnlineTV(PluginCanHandleUrl):
    __plugin__ = OnlineTV

    should_match = [
        "https://onlinetv.one/video/gubka-bob-kvadratnye-shtany-smotret-onlain-vse-serii-podrjad.html",
    ]

    should_not_match = [
        "https://onlinetv.one/video/igry",
        "https://support.onlinetv.one/video/igry",
    ]
