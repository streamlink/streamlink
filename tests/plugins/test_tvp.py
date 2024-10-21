from streamlink.plugins.tvp import TVP
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVP(PluginCanHandleUrl):
    __plugin__ = TVP

    should_match_groups = [
        # live
        (("default", "https://stream.tvp.pl"), {}),
        (("default", "https://stream.tvp.pl/"), {}),
        (("default", "https://stream.tvp.pl/?channel_id=1455"), {"channel_id": "1455"}),  # TVP info
        (("default", "https://stream.tvp.pl/?channel_id=51656487"), {"channel_id": "51656487"}),  # TVP world
        # old live URLs
        (("default", "https://tvpstream.vod.tvp.pl"), {}),
        (("default", "https://tvpstream.vod.tvp.pl/"), {}),
        (("default", "https://tvpstream.vod.tvp.pl/?channel_id=1455"), {"channel_id": "1455"}),
        (("default", "https://tvpstream.vod.tvp.pl/?channel_id=51656487"), {"channel_id": "51656487"}),
        # VOD
        (
            ("vod", "https://vod.tvp.pl/filmy-dokumentalne,163/krolowa-wladczyni-i-matka,284734"),
            {"vod_id": "284734"},
        ),
        # VOD episode
        (
            ("vod", "https://vod.tvp.pl/programy,88/eurowizja-odcinki,276170/odcinek-4,S05E04,1302944"),
            {"vod_id": "1302944"},
        ),
        # tvp.info
        (
            (
                "tvp_info",
                "https://www.tvp.info/78213165/euro-2024-polska-holandia-12-bartosz-salamon-czuje-sie-winny-za-te-porazke-wideo",
            ),
            {},
        ),
        # sport.tvp
        (
            (
                "tvp_sport",
                "https://sport.tvp.pl/79514191/paryz-2024-magda-linette-mirra-andriejewa-1-runda-na-zywo-transmisja-online-live-stream-igrzyska-olimpijskie-2872024",
            ),
            {"stream_id": "79514191"},
        ),
    ]

    should_not_match = [
        "https://tvp.pl/",
        "https://vod.tvp.pl/",
    ]
