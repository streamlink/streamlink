from streamlink.plugins.delfi import Delfi
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDelfi(PluginCanHandleUrl):
    __plugin__ = Delfi

    should_match = [
        # delfi.lt live (YouTube)
        "https://www.delfi.lt/video/tv/",
        # delfi.lt VOD
        "https://www.delfi.lt/video/laidos/dakaras/dakaras-2022-koki-tiksla-turi-pirmasis-lietuviskas-sunkvezimio-ekipazas.d"
        + "?id=89058633",

        # delfi.lv VOD
        "http://www.delfi.lv/delfi-tv-ar-jani-domburu/pilnie-raidijumi/delfi-tv-ar-jani-domburu-atbild"
        + "-veselibas-ministre-anda-caksa-pilna-intervija?id=49515013",
        # delfi.lv VOD (YouTube)
        "https://www.delfi.lv/news/national/politics/video-gads-ko-varetu-aizmirst-bet-nesanak-spilgtako-notikumu-atskats.d"
        + "?id=53912761",

        # delfi.ee live
        "https://sport.delfi.ee/artikkel/95517317/otse-delfi-tv-s-kalevcramo-voitis-tartu-ulikooli-vastu-avapoolaja-14"
        + "-punktiga",
    ]
