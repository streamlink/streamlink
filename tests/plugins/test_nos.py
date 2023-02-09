from streamlink.plugins.nos import NOS
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNOS(PluginCanHandleUrl):
    __plugin__ = NOS

    should_match = [
        "https://nos.nl/livestream/2220100-wk-sprint-schaatsen-1-000-meter-mannen.html",
        "https://nos.nl/collectie/13781/livestream/2385081-ek-voetbal-engeland-schotland",
        "https://nos.nl/collectie/13781/livestream/2385461-ek-voetbal-voorbeschouwing-italie-wales-18-00-uur",
        "https://nos.nl/collectie/13781/video/2385846-ek-in-2-21-gosens-show-tegen-portugal-en-weer-volle-bak-in-boedapest",
        "https://nos.nl/video/2385779-dronebeelden-tonen-spoor-van-vernieling-bij-leersum",
        "https://nos.nl/uitzendingen",
        "https://nos.nl/uitzendingen/livestream/2385462",
    ]

    should_not_match = [
        "https://nos.nl/artikel/2385784-explosieve-situatie-leidde-tot-verwoeste-huizen-en-omgewaaide-bomen-leersum",
    ]
