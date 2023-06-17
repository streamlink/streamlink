from streamlink.plugins.erttv import ERTTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlERTTV(PluginCanHandleUrl):
    __plugin__ = ERTTV

    should_match = [
        "https://www.ert.gr/webtv/ert/tv/live-glm/ert1.html",
        "https://www.ert.gr/webtv/ert/tv/live-glm/ert2.html",
        "https://www.ert.gr/webtv/ert/tv/live-glm/ert3.html",
    ]
