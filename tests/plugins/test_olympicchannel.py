from streamlink.plugins.olympicchannel import OlympicChannel
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlOlympicChannel(PluginCanHandleUrl):
    __plugin__ = OlympicChannel

    should_match = [
        "https://www.olympicchannel.com/en/video/detail/stefanidi-husband-coach-krier-relationship/",
        "https://www.olympicchannel.com/en/live/",
        "https://www.olympicchannel.com/en/live/video/detail/olympic-ceremonies-channel/",
        "https://www.olympicchannel.com/de/video/detail/stefanidi-husband-coach-krier-relationship/",
        "https://www.olympicchannel.com/de/original-series/detail/body/body-season-season-1/episodes/"
        + "treffen-sie-aaron-wheelz-fotheringham-den-paten-des-rollstuhl-extremsports/",
    ]

    should_not_match = [
        "https://www.olympicchannel.com/en/",
        "https://www.olympicchannel.com/en/channel/olympic-channel/",
    ]
