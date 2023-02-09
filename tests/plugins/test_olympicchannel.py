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
        "https://olympics.com/en/sport-events/2021-fiba-3x3-olympic-qualifier-graz/?"
        + "slug=final-day-fiba-3x3-olympic-qualifier-graz",
        "https://olympics.com/en/video/spider-woman-shauna-coxsey-great-britain-climbing-interview",
        "https://olympics.com/en/original-series/episode/how-fun-fuels-this-para-taekwondo-world-champion-unleash-the-new",
        "https://olympics.com/tokyo-2020/en/news/videos/tokyo-2020-1-message",
    ]

    should_not_match = [
        "https://www.olympicchannel.com/en/",
        "https://www.olympics.com/en/",
        "https://olympics.com/tokyo-2020/en/",
    ]
