from streamlink.plugins.lnk import LNK
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLNK(PluginCanHandleUrl):
    __plugin__ = LNK

    should_match = [
        "https://lnk.lt/tiesiogiai",
        "https://lnk.lt/tiesiogiai#lnk",
        "https://lnk.lt/tiesiogiai#btv",
        "https://lnk.lt/tiesiogiai#2tv",
        "https://lnk.lt/tiesiogiai#infotv",
        "https://lnk.lt/tiesiogiai#tv1",
    ]

    should_not_match = [
        "https://lnk.lt/",
        "https://lnk.lt/vaikams",
        "https://lnk.lt/zinios/Visi/157471",
    ]
