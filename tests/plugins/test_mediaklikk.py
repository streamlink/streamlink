from streamlink.plugins.mediaklikk import Mediaklikk
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMediaklikk(PluginCanHandleUrl):
    __plugin__ = Mediaklikk

    should_match = [
        "https://www.mediaklikk.hu/duna-world-elo/",
        "https://www.mediaklikk.hu/duna-world-radio-elo",
        "https://www.mediaklikk.hu/m1-elo",
        "https://www.mediaklikk.hu/m2-elo",
        "https://mediaklikk.hu/video/hirado-2021-06-24-i-adas-6/",
        "https://m4sport.hu/elo/",
        "https://m4sport.hu/elo/?channelId=m4sport+",
        "https://m4sport.hu/elo/?showchannel=mtv4plus",
        "https://m4sport.hu/euro2020-video/goool2-13-resz",
        "https://hirado.hu/videok/",
        "https://hirado.hu/videok/nemzeti-sporthirado-2021-06-24-i-adas-2/",
        "https://petofilive.hu/video/2021/06/23/the-anahit-klip-limited-edition/",
    ]
