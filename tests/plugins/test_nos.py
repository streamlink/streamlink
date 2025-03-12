from streamlink.plugins.nos import NOS
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNOS(PluginCanHandleUrl):
    __plugin__ = NOS

    should_match = [
        "https://nos.nl/live",
        "https://nos.nl/livestream/2539164-schaatsen-wb-milwaukee-straks-de-massastart-m",
        "https://nos.nl/collectie/13951/video/2491092-dit-was-prinsjesdag",
        "https://nos.nl/l/2490788",
        "https://nos.nl/video/2490788-meteoor-gespot-boven-noord-nederland",
    ]

    should_not_match = [
        "https://nos.nl/livestream",
        "https://nos.nl/l",
        "https://nos.nl/video",
        "https://nos.nl/collectie",
        "https://nos.nl/artikel/2385784-explosieve-situatie-leidde-tot-verwoeste-huizen-en-omgewaaide-bomen-leersum",
        "https://nos.nl/sport",
        "https://nos.nl/sport/videos",
        "https://nos.nl/programmas",
        "https://nos.nl/uitzendingen",
        "https://nos.nl/uitzendingen/livestream/2385462",
    ]
