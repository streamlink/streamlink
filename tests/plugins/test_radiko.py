from streamlink.plugins.radiko import Radiko
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRadiko(PluginCanHandleUrl):
    __plugin__ = Radiko

    should_match = [
        "https://radiko.jp/#!/live/QRR",
        "https://radiko.jp/#!/ts/YFM/20201206010000",
        "http://radiko.jp/#!/live/QRR",
        "http://radiko.jp/live/QRR",
        "http://radiko.jp/#!/ts/QRR/20200308180000",
        "http://radiko.jp/ts/QRR/20200308180000",
    ]
