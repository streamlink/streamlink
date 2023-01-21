from streamlink.plugins.tvp import TVP
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVP(PluginCanHandleUrl):
    __plugin__ = TVP

    should_match_groups = [
        # live
        ("https://stream.tvp.pl", {}),
        ("https://stream.tvp.pl/", {}),
        ("https://stream.tvp.pl/?channel_id=63759349", {"channel_id": "63759349"}),
        ("https://stream.tvp.pl/?channel_id=14812849", {"channel_id": "14812849"}),
        # old live URLs
        ("https://tvpstream.vod.tvp.pl", {}),
        ("https://tvpstream.vod.tvp.pl/", {}),
        ("https://tvpstream.vod.tvp.pl/?channel_id=63759349", {"channel_id": "63759349"}),
        ("https://tvpstream.vod.tvp.pl/?channel_id=14812849", {"channel_id": "14812849"}),

        # VOD
        (
            "https://vod.tvp.pl/filmy-dokumentalne,163/krolowa-wladczyni-i-matka,284734",
            {"vod_id": "284734"},
        ),
        # VOD episode
        (
            "https://vod.tvp.pl/programy,88/z-davidem-attenborough-dokola-swiata-odcinki,284703/odcinek-2,S01E02,319220",
            {"vod_id": "319220"},
        ),

        # tvp.info
        (("tvp_info", "https://tvp.info/"), {}),
        (("tvp_info", "https://www.tvp.info/"), {}),
        (("tvp_info", "https://www.tvp.info/65275202/13012023-0823"), {}),
    ]

    should_not_match = [
        "https://tvp.pl/",
        "https://vod.tvp.pl/",
    ]
