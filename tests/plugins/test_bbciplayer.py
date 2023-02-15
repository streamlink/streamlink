import unittest

from streamlink.plugins.bbciplayer import BBCiPlayer
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBBCiPlayer(PluginCanHandleUrl):
    __plugin__ = BBCiPlayer

    should_match = [
        "http://www.bbc.co.uk/iplayer/episode/b00ymh67/madagascar-1-island-of-marvels",
        "http://www.bbc.co.uk/iplayer/live/bbcone",
    ]

    should_not_match = [
        "http://www.bbc.co.uk/iplayer/",
    ]


class TestPluginBBCiPlayer(unittest.TestCase):
    def test_vpid_hash(self):
        assert BBCiPlayer._hash_vpid("1234567890") == "71c345435589c6ddeea70d6f252e2a52281ecbf3"
