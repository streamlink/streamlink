from streamlink.plugins.bbciplayer import BBCiPlayer
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBBCiPlayer(PluginCanHandleUrl):
    __plugin__ = BBCiPlayer

    should_match_groups = [
        (
            ("live", "http://www.bbc.co.uk/iplayer/live/bbcone"),
            {"channel_name": "bbcone"},
        ),
        (
            ("episode", "http://www.bbc.co.uk/iplayer/episode/b00ymh67/madagascar-1-island-of-marvels"),
            {"episode_id": "b00ymh67"},
        ),
    ]

    should_not_match = [
        "http://www.bbc.co.uk/iplayer/",
    ]


class TestPluginBBCiPlayer:
    def test_vpid_hash(self):
        assert BBCiPlayer._hash_vpid("1234567890") == "71c345435589c6ddeea70d6f252e2a52281ecbf3"
