from streamlink.plugins.kugou import Kugou
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlKugou(PluginCanHandleUrl):
    __plugin__ = Kugou

    should_match = [
        "https://fanxing.kugou.com/1062645?refer=605",
        "https://fanxing.kugou.com/77997777?refer=605",
        "https://fanxing.kugou.com/1047927?refer=605",
        "https://fanxing.kugou.com/1048570?refer=605",
        "https://fanxing.kugou.com/1062642?refer=605",
        "https://fanxing.kugou.com/1071651",
    ]
