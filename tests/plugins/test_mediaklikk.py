from streamlink.plugins.mediaklikk import Mediaklikk
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMediaklikk(PluginCanHandleUrl):
    __plugin__ = Mediaklikk

    should_match = [
        "https://www.mediaklikk.hu/duna-world-elo/",
        "https://www.mediaklikk.hu/m1-elo",
        "https://www.mediaklikk.hu/m2-elo",
        "https://m4sport.hu/elo/",
        "https://m4sport.hu/elo/?channelId=m4sport+",
        "https://m4sport.hu/elo/?showchannel=mtv4plus",
        "https://m4sport.hu/video/2025/08/08/fizz-liga-kolorcity-kazincbarcika-sc-dvsc-merkozes",
        "https://hirado.hu/elo/m1",
        "https://hirado.hu/elo/m2",
        "https://hirado.hu/belfold/video/2025/08/09/szuletesnap-a-budapesti-allat-es-novenykertben",
    ]
