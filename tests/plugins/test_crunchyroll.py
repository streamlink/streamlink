from streamlink.plugins.crunchyroll import Crunchyroll
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCrunchyroll(PluginCanHandleUrl):
    __plugin__ = Crunchyroll

    should_match = [
        "http://www.crunchyroll.com/idol-incidents/episode-1-why-become-a-dietwoman-728233",
        "http://www.crunchyroll.com/ru/idol-incidents/episode-1-why-become-a-dietwoman-728233",
        "http://www.crunchyroll.com/idol-incidents/media-728233",
        "http://www.crunchyroll.com/fr/idol-incidents/media-728233",
        "http://www.crunchyroll.com/media-728233",
        "http://www.crunchyroll.com/de/media-728233",
        "http://www.crunchyroll.fr/media-728233",
        "http://www.crunchyroll.fr/es/media-728233"
    ]

    should_not_match = [
        "http://www.crunchyroll.com/gintama",
        "http://www.crunchyroll.es/gintama",
    ]
