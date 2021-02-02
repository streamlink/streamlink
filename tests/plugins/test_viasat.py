from streamlink.plugins.viasat import Viasat
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlViasat(PluginCanHandleUrl):
    __plugin__ = Viasat

    should_match = [
        "http://www.juicyplay.dk/story/se-robinson-benjamins-store-forandring",
        "http://www.tv3.dk/paradise-hotel/paradise-hotel-2018-her-er-deltagerne",
        "http://www.tv3.dk/paradise-hotel/paradise-hotel-2018-her-er-deltagerne",
        "https://play.tv3.lt/programos/eurocup/903167?autostart=true",
        "https://play.tv3.lt/programos/pamilti-vel/903174?autostart=true",
        "https://skaties.lv/sports/futbols/video-liverpool-izbraukuma-rada-klasi-pret-bournemouth/",
        "https://tv3play.tv3.ee/sisu/eesti-otsib-superstaari",
        "https://tv3play.tv3.ee/sisu/inglite-aeg/902432?autostart=true",
        "https://tvplay.skaties.lv/parraides/darma-un-gregs/902597?autostart=true&collection=719",
        "https://tvplay.skaties.lv/parraides/kungfu-panda/900510?autostart=true",
        "https://www.tv3.lt/naujiena/938699/ispudingiausi-kobe-bryanto-karjeros-epizodai-monstriski-dejimai-ir"
        + "-pergalingi-metimai",
        "https://www.tv6play.no/programmer/underholdning/paradise-hotel-sverige/sesong-8/episode-19",
        "https://www.tv6play.no/programmer/underholdning/paradise-hotel/sesong-9/822763",
        "https://www.viafree.dk/",
        "https://www.viafree.dk/embed?id=898974&wmode=transparent&autostart=true",
        "https://www.viafree.dk/programmer/reality/forside-fruer/saeson-2/872877",
        "https://www.viafree.dk/programmer/reality/forside-fruer/saeson-2/episode-1",
        "https://www.viafree.no/programmer/underholdning/paradise-hotel-sverige/sesong-8/episode-19",
        "https://www.viafree.no/programmer/underholdning/paradise-hotel/sesong-9/822763",
        "https://www.viafree.se/program/underhallning/det-stora-experimentet/sasong-1/897870",
        "https://www.viafree.se/program/underhallning/det-stora-experimentet/sasong-1/avsnitt-19",
    ]

    should_not_match = [
        "http://www.tv3play.no",
        "http://www.tv6play.se",
    ]
