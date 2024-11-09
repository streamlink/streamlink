from streamlink.plugins.tv4play import TV4Play
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTV4Play(PluginCanHandleUrl):
    __plugin__ = TV4Play

    should_match_groups = [
        (
            (
                "default",
                "https://www.tv4play.se/program/robinson/del-26-sasong-2021/13299862",
            ),
            {"video_id": "13299862"},
        ),
        (
            (
                "default",
                "https://www.tv4play.se/program/sverige-mot-norge/del-1-sasong-1/12490380",
            ),
            {"video_id": "12490380"},
        ),
        (
            (
                "default",
                "https://www.tv4play.se/program/nyheterna/live/10378590",
            ),
            {"video_id": "10378590"},
        ),
        (
            (
                "fotbollskanalen",
                "https://www.fotbollskanalen.se/video/10395484/ghoddos-fullbordar-vandningen---ger-ofk-ledningen/",
            ),
            {"video_id": "10395484"},
        ),
    ]
