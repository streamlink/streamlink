from streamlink.plugins.svtplay import SVTPlay
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSVTPlay(PluginCanHandleUrl):
    __plugin__ = SVTPlay

    should_match = [
        "https://www.svtplay.se/kanaler/svt1",
        "https://www.svtplay.se/kanaler/svt2?start=auto",
        "https://www.svtplay.se/kanaler/svtbarn",
        "https://www.svtplay.se/kanaler/kunskapskanalen?start=auto",
        "https://www.svtplay.se/kanaler/svt24?start=auto",
        "https://www.svtplay.se/video/27659457/den-giftbla-floden?start=auto",
        "https://www.svtplay.se/video/27794015/100-vaginor",
        "https://www.svtplay.se/video/28065172/motet/motet-sasong-1-det-skamtar-du-inte-om",
        "https://www.svtplay.se/dokument-inifran-att-radda-ett-barn",
    ]

    should_not_match = [
        "http://www.svtflow.se/video/2020285/avsnitt-6",
        "https://www.svtflow.se/video/2020285/avsnitt-6",
    ]
