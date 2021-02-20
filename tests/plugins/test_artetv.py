from streamlink.plugins.artetv import ArteTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlArteTV(PluginCanHandleUrl):
    __plugin__ = ArteTV

    should_match = [
        # new url
        "http://www.arte.tv/fr/direct/",
        "http://www.arte.tv/de/live/",
        "http://www.arte.tv/de/videos/074633-001-A/gesprach-mit-raoul-peck",
        "http://www.arte.tv/en/videos/071437-010-A/sunday-soldiers",
        "http://www.arte.tv/fr/videos/074633-001-A/entretien-avec-raoul-peck",
        "http://www.arte.tv/pl/videos/069873-000-A/supermama-i-businesswoman",

        # old url - some of them get redirected and some are 404
        "http://www.arte.tv/guide/fr/direct",
        "http://www.arte.tv/guide/de/live",
        "http://www.arte.tv/guide/fr/024031-000-A/le-testament-du-docteur-mabuse",
        "http://www.arte.tv/guide/de/024031-000-A/das-testament-des-dr-mabuse",
        "http://www.arte.tv/guide/en/072544-002-A/christmas-carols-from-cork",
        "http://www.arte.tv/guide/es/068380-000-A/una-noche-en-florencia",
        "http://www.arte.tv/guide/pl/068916-006-A/belle-and-sebastian-route-du-rock",
    ]

    should_not_match = [
        # shouldn't match
        "http://www.arte.tv/guide/fr/plus7/",
        "http://www.arte.tv/guide/de/plus7/",
        # shouldn't match - playlists without video ids in url
        "http://www.arte.tv/en/videos/RC-014457/the-power-of-forests/",
        "http://www.arte.tv/en/videos/RC-013118/street-art/",
    ]
