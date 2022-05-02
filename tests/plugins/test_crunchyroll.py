from streamlink.plugins.crunchyroll import Crunchyroll
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCrunchyroll(PluginCanHandleUrl):
    __plugin__ = Crunchyroll

    should_match_groups = [
        ("http://www.crunchyroll.com/idol-incidents/episode-1-a-title-728233", {"media_id": "728233"}),
        ("http://www.crunchyroll.com/ru/idol-incidents/episode-1-a-title-728233", {"media_id": "728233"}),
        ("http://www.crunchyroll.com/idol-incidents/media-728233", {"media_id": "728233"}),
        ("http://www.crunchyroll.com/fr/idol-incidents/media-728233", {"media_id": "728233"}),
        ("http://www.crunchyroll.com/media-728233", {"media_id": "728233"}),
        ("http://www.crunchyroll.com/de/media-728233", {"media_id": "728233"}),
        ("http://www.crunchyroll.fr/media-728233", {"media_id": "728233"}),
        ("http://www.crunchyroll.fr/es/media-728233", {"media_id": "728233"}),
        ("https://beta.crunchyroll.com/watch/GRNQ5DDZR/Game-Over", {"beta_id": "GRNQ5DDZR"}),
        ("https://beta.crunchyroll.com/watch/ValidID123/any/thing?x&y", {"beta_id": "ValidID123"}),
    ]

    should_not_match = [
        "http://www.crunchyroll.com/gintama",
        "http://www.crunchyroll.es/gintama",
        "http://beta.crunchyroll.com/",
        "http://beta.crunchyroll.com/something",
        "http://beta.crunchyroll.com/watch/",
        "http://beta.crunchyroll.com/watch/not-a-valid-id",
        "http://beta.crunchyroll.com/watch/not-a-valid-id/a-title",
    ]
