from streamlink.plugins.pluto import Pluto
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPluto(PluginCanHandleUrl):
    __plugin__ = Pluto

    should_match_groups = [
        (
            (
                "live",
                "https://pluto.tv/en/live-tv/61409f8d6feb30000766b675",
            ),
            {
                "id": "61409f8d6feb30000766b675",
            },
        ),
        (
            (
                "series",
                "https://pluto.tv/en/on-demand/series/5e00cd538e67b0dcb2cf3bcd/season/1/episode/60dee91cfc802600134b886d",
            ),
            {
                "id_s": "5e00cd538e67b0dcb2cf3bcd",
                "id_e": "60dee91cfc802600134b886d",
            },
        ),
        (
            (
                "movies",
                "https://pluto.tv/en/on-demand/movies/600545d1813b2d001b686fa9",
            ),
            {
                "id": "600545d1813b2d001b686fa9",
            },
        ),
        (
            (
                "series",
                "https://pluto.tv/gsa/shows/2740225/episode/60dee91cfc802600134b886d/",
            ),
            {
                "id_s": "2740225",
                "id_e": "60dee91cfc802600134b886d",
            },
        ),
        (
            (
                "movies",
                "https://pluto.tv/us/movies/6925771d1a8e9be91b1b7d22/#open",
            ),
            {
                "id": "6925771d1a8e9be91b1b7d22",
            },
        ),
        (
            (
                "live",
                "https://pluto.tv/fr/watch/live-tv/31528/",
            ),
            {
                "id": "31528",
            },
        ),
    ]

    should_not_match = [
        "https://pluto.tv/live-tv",
    ]
