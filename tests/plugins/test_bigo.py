from streamlink.plugins.bigo import Bigo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBigo(PluginCanHandleUrl):
    __plugin__ = Bigo

    should_match = [
        "https://www.bigo.tv/SITE_ID",
    ]
