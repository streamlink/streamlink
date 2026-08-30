from streamlink.plugins.ssh101 import SSH101
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSSH101(PluginCanHandleUrl):
    __plugin__ = SSH101

    should_match = [
        "http://ssh101.com/live/sarggg",
        "https://ssh101.com/detail.php?id=user",
        "https://www.ssh101.com/live/aigaiotvlive",
        "https://www.ssh101.com/securelive/index.php?id=aigaiotvlive",
    ]

    should_not_match = [
        "https://ssh101.com/m3u8/dyn/aigaiotvlive/index.m3u8",
    ]
