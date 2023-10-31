from streamlink.plugins.tvp import TVP
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVP(PluginCanHandleUrl):
    __plugin__ = TVP

    should_match_groups = [
        # live
        (("default", "https://stream.tvp.pl"), {}),
        (("default", "https://stream.tvp.pl/"), {}),
        (("default", "https://stream.tvp.pl/?channel_id=63759349"), {"channel_id": "63759349"}),
        (("default", "https://stream.tvp.pl/?channel_id=14812849"), {"channel_id": "14812849"}),
        # old live URLs
        (("default", "https://tvpstream.vod.tvp.pl"), {}),
        (("default", "https://tvpstream.vod.tvp.pl/"), {}),
        (("default", "https://tvpstream.vod.tvp.pl/?channel_id=63759349"), {"channel_id": "63759349"}),
        (("default", "https://tvpstream.vod.tvp.pl/?channel_id=14812849"), {"channel_id": "14812849"}),

        # VOD
        (
            ("vod", "https://vod.tvp.pl/filmy-dokumentalne,163/krolowa-wladczyni-i-matka,284734"),
            {"vod_id": "284734"},
        ),
        # VOD episode
        (
            ("vod", "https://vod.tvp.pl/programy,88/z-davidem-attenborough-dokola-swiata-odcinki,284703/odcinek-2,S01E02,319220"),
            {"vod_id": "319220"},
        ),

        # tvp.info
        (("tvp_info", "https://www.tvp.info/72577058/28092023-0823"), {}),
        (("tvp_info", "https://www.tvp.info/73805503/przygotowania-do-uroczystosci-wszystkich-swietych"), {}),
    ]

    should_not_match = [
        "https://tvp.pl/",
        "https://vod.tvp.pl/",
    ]
